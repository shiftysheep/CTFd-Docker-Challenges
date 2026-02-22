from __future__ import annotations

import hashlib
import json
import logging
from typing import TYPE_CHECKING

from ..functions.general import _find_available_port, do_request, get_required_ports, get_secrets

# Type-only imports: keeps functions testable without SQLAlchemy initialization.
# Runtime model access uses lazy imports inside individual functions.
if TYPE_CHECKING:
    from ..models.models import DockerConfig, DockerServiceChallenge


def _assign_service_ports(needed_ports: list, blocked_ports: list) -> list:
    """
    Assign random available ports from PORT_ASSIGNMENT_MIN-PORT_ASSIGNMENT_MAX range for service endpoints.

    Args:
        needed_ports: List of port/protocol strings (e.g., ["80/tcp", "443/tcp"])
        blocked_ports: List of ports already in use

    Returns:
        List of port binding dictionaries for Docker service EndpointSpec
    """
    assigned_ports = []
    for port_spec in needed_ports:
        port = _find_available_port(blocked_ports)
        port_dict = {
            "PublishedPort": port,
            "PublishMode": "ingress",
            "Protocol": "tcp",
            "TargetPort": int(port_spec.split("/")[0]),
            "Name": f"Exposed Port {port_spec}",
        }
        assigned_ports.append(port_dict)
    return assigned_ports


def _parse_docker_secrets(raw: str | None) -> list[dict]:
    """Parse docker_secrets JSON field into list of {id, protected} dicts."""
    if not raw or raw == "[]":
        return []
    return json.loads(raw)


def _build_secrets_list(challenge: DockerServiceChallenge, docker: DockerConfig) -> list:
    """
    Build Docker secrets list with file permissions for service configuration.

    Args:
        challenge: DockerServiceChallenge instance with secret IDs and permissions
        docker: DockerConfig for fetching available secrets

    Returns:
        List of secret mount dictionaries for Docker service TaskTemplate
    """
    all_secrets = get_secrets(docker)
    secrets_list = []
    secret_configs = _parse_docker_secrets(challenge.docker_secrets)

    for config in secret_configs:
        secret_id = config["id"]
        permissions = 0o600 if config.get("protected", False) else 0o777

        for secret in all_secrets:
            if secret_id == secret["ID"]:
                secrets_list.append(
                    {
                        "File": {
                            "Name": f"/run/secrets/{secret['Name']}",
                            "UID": "1",
                            "GID": "1",
                            "Mode": permissions,
                        },
                        "SecretID": secret_id,
                        "SecretName": secret["Name"],
                    }
                )
                break
    return secrets_list


def create_service(
    docker: DockerConfig, challenge_id: int, image: str, team: str, portbl: list
) -> tuple[str | None, str | None]:
    """
    Create a Docker Swarm service for a challenge instance.

    Args:
        docker: DockerConfig instance with API connection details
        challenge_id: Database ID of the challenge
        image: Docker image name (e.g., "registry/image:tag")
        team: Team identifier for unique service naming
        portbl: List of blocked ports to avoid conflicts

    Returns:
        Tuple of (instance_id, service_data) or (None, None) on failure
    """
    # Get challenge configuration
    from ..models.models import DockerServiceChallenge as _ServiceChallenge

    challenge = _ServiceChallenge.query.filter_by(id=challenge_id).first()
    exposed_ports = challenge.exposed_ports if challenge else None
    needed_ports = get_required_ports(docker, image, exposed_ports)

    # Generate unique service name
    # MD5 used for service naming only, not security
    team_hash = hashlib.md5(team.encode("utf-8"), usedforsecurity=False).hexdigest()[:10]
    service_name = f"svc_{image.split(':')[1]}{team_hash}"

    # Assign available ports and build secrets list
    assigned_ports = _assign_service_ports(needed_ports, portbl)
    secrets_list = _build_secrets_list(challenge, docker)

    # Build service creation request
    data = json.dumps(
        {
            "Name": service_name,
            "TaskTemplate": {"ContainerSpec": {"Image": image, "Secrets": secrets_list}},
            "EndpointSpec": {"Mode": "vip", "Ports": assigned_ports},
        }
    )

    # Create service and handle response
    r = do_request(docker, url="/services/create", method="POST", data=data)
    if not r:
        return None, None

    instance_id = r.json().get("ID")
    if not instance_id:
        logging.error("Unable to create service %s with image %s", service_name, image)
        logging.error("Error: %s", r.json())
        return None, None

    return instance_id, data


def delete_service(docker: DockerConfig, instance_id: str) -> bool:
    """
    Delete a Docker Swarm service by ID.

    Args:
        docker: DockerConfig instance with API connection details
        instance_id: Docker service ID to delete

    Returns:
        True if deletion succeeded or service already gone, False otherwise.
    """
    r = do_request(docker, f"/services/{instance_id}", method="DELETE")
    if r is None:
        return False
    if r.status_code == 404:
        return True  # Service already gone — desired state achieved
    return r.ok
