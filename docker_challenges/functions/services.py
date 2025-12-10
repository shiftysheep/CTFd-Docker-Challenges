import hashlib
import json
import random

from ..constants import (
    MAX_PORT_ASSIGNMENT_ATTEMPTS,
    PORT_ASSIGNMENT_MAX,
    PORT_ASSIGNMENT_MIN,
)
from ..functions.general import do_request, get_required_ports, get_secrets
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
        assigned_port = None
        for _attempt in range(MAX_PORT_ASSIGNMENT_ATTEMPTS):
            # random.choice used for port assignment, not cryptographic purposes
            candidate_port = random.choice(range(PORT_ASSIGNMENT_MIN, PORT_ASSIGNMENT_MAX))  # noqa: S311
            if candidate_port not in blocked_ports:
                assigned_port = candidate_port
                port_dict = {
                    "PublishedPort": assigned_port,
                    "PublishMode": "ingress",
                    "Protocol": "tcp",
                    "TargetPort": int(port_spec.split("/")[0]),
                    "Name": f"Exposed Port {port_spec}",
                }
                assigned_ports.append(port_dict)
                break

        if assigned_port is None:
            raise RuntimeError(
                f"Failed to find available port after {MAX_PORT_ASSIGNMENT_ATTEMPTS} attempts. "
                f"Port range {PORT_ASSIGNMENT_MIN}-{PORT_ASSIGNMENT_MAX} may be exhausted."
            )
    return assigned_ports


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
    permissions = 0o600 if challenge.protect_secrets else 0o777

    for image_secret in challenge.docker_secrets.split(","):
        for secret in all_secrets:
            if image_secret == secret["ID"]:
                secrets_list.append(
                    {
                        "File": {
                            "Name": f"/run/secrets/{secret['Name']}",
                            "UID": "1",
                            "GID": "1",
                            "Mode": permissions,
                        },
                        "SecretID": image_secret,
                        "SecretName": secret["Name"],
                    }
                )
                break
    return secrets_list


def create_service(docker: DockerConfig, challenge_id: int, image: str, team: str, portbl: list):
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
    challenge = DockerServiceChallenge.query.filter_by(id=challenge_id).first()
    exposed_ports = challenge.exposed_ports if challenge else None
    needed_ports = get_required_ports(docker, image, exposed_ports)

    # Generate unique service name
    # MD5 used for service naming only, not security
    team_hash = hashlib.md5(team.encode("utf-8")).hexdigest()[:10]  # noqa: S324
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
    instance_id = r.json().get("ID")
    if not instance_id:
        print(f"Unable to create service {service_name} with image {image}")
        print(f"Error: {r.json()}")
        return None, None

    return instance_id, data


def delete_service(docker: DockerConfig, instance_id: str) -> bool:
    r = do_request(docker, f"/services/{instance_id}", method="DELETE")
    return r.ok
