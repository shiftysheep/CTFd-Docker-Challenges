from __future__ import annotations

import hashlib
import json
import logging
from typing import TYPE_CHECKING

from ..functions.general import _find_available_port, do_request, get_required_ports

# Type-only imports: keeps functions testable without SQLAlchemy initialization.
# Runtime model access uses lazy imports inside individual functions.
if TYPE_CHECKING:
    from ..models.models import DockerConfig


def find_existing(docker: DockerConfig, name: str) -> str | None:
    """
    Find existing Docker container by name.

    Returns:
        Container ID if found, None otherwise
    """
    r = do_request(docker, url=f'/containers/json?all=1&filters={{"name":["{name}"]}}')

    if not r:
        logging.error("Failed to contact Docker!")
        return None

    if len(r.json()) == 1:
        return r.json()[0]["Id"]

    return None


def _assign_container_ports(needed_ports: list[str], blocked_ports: list[int]) -> dict[str, dict]:
    """
    Assign random available ports from PORT_ASSIGNMENT_MIN-PORT_ASSIGNMENT_MAX range for containers.

    Args:
        needed_ports: List of port/protocol strings (e.g., ["80/tcp", "443/tcp"])
        blocked_ports: List of ports already in use

    Returns:
        Dictionary mapping port strings to empty dicts for Docker PortBindings
    """
    assigned_ports = {}

    for _i in needed_ports:
        port = _find_available_port(blocked_ports)
        assigned_ports[f"{port}/tcp"] = {}

    return assigned_ports


def create_container(
    docker: DockerConfig,
    image: str,
    team: str,
    portbl: list[int],
    exposed_ports: str | None = None,
) -> tuple[str, str] | tuple[None, None]:
    """
    Create a standalone Docker container for a challenge instance.

    Args:
        docker: DockerConfig instance with API connection details
        image: Docker image name (e.g., "registry/image:tag")
        team: Team/user identifier for unique container naming
        portbl: List of blocked ports to avoid conflicts
        exposed_ports: Optional comma-separated port specs (e.g., "80/tcp,443/tcp")

    Returns:
        Tuple of (container_id, container_name) on success.
    """
    needed_ports = get_required_ports(docker, image, exposed_ports)
    # MD5 used for container naming only, not security
    team = hashlib.md5(team.encode("utf-8"), usedforsecurity=False).hexdigest()[:10]
    container_name = "{}_{}".format(
        image.replace(":", "_").replace("/", "_").replace(".", "_"),
        team,
    )

    # Assign random available ports
    assigned_ports = _assign_container_ports(needed_ports, portbl)

    ports = {}
    bindings = {}
    tmp_ports = list(assigned_ports.keys())
    for i in needed_ports:
        ports[i] = {}
        bindings[i] = [{"HostPort": tmp_ports.pop()}]
    data = json.dumps(
        {
            "Image": image,
            "ExposedPorts": ports,
            "HostConfig": {"PortBindings": bindings},
            "AutoRemove": True,
        }
    )

    r = do_request(
        docker,
        url=f"/containers/create?name={container_name}",
        method="POST",
        data=data,
    )
    if not r:
        return None, None
    instance_id = find_existing(docker, container_name) if r.status_code == 409 else r.json()["Id"]
    if instance_id is None:
        return None, None

    do_request(docker, url=f"/containers/{instance_id}/start", method="POST")

    return instance_id, data


def delete_container(docker: DockerConfig, instance_id: str) -> bool:
    """
    Delete a Docker container by ID with force flag.

    Args:
        docker: DockerConfig instance with API connection details
        instance_id: Docker container ID to delete

    Returns:
        True if deletion succeeded or container already gone, False otherwise.
    """
    r = do_request(docker, f"/containers/{instance_id}?force=true", method="DELETE")
    if not r:
        return False
    if r.status_code == 404:
        return True  # Container already gone — desired state achieved
    return r.ok
