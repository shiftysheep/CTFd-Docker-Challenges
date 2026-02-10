from __future__ import annotations

import base64
import json
import logging
from typing import TYPE_CHECKING, Any, Callable

import requests
from requests import Response
from requests.exceptions import RequestException, Timeout

# Type-only imports: keeps functions testable without SQLAlchemy initialization.
# Runtime model access uses lazy imports inside individual functions.
if TYPE_CHECKING:
    from ..models.models import DockerChallengeTracker, DockerConfig


def do_request(
    docker: DockerConfig,
    url: str,
    headers: dict[str, str] | None = None,
    method: str = "GET",
    data: dict | str | None = None,
) -> Response | None:
    """
    Execute HTTP request to Docker API with optional TLS support.

    Args:
        docker: DockerConfig instance containing hostname and TLS settings
        url: API endpoint path (e.g., "/containers/json")
        headers: Optional custom headers (defaults to application/json)
        method: HTTP method - GET, POST, DELETE, etc. (default: GET)
        data: Optional request body as dict or JSON string

    Returns:
        Response object on success, None on connection failure.
        Handles TLS certificate validation when docker.tls_enabled is True.
    """
    tls = docker.tls_enabled
    prefix = "https" if tls else "http"
    host = docker.hostname
    base = f"{prefix}://{host}"

    # If no host set, request will fail
    if not host:
        return None

    if not headers:
        headers = {"Content-Type": "application/json"}

    request_args = {
        "url": f"{base}{url}",
        "headers": headers,
        "method": method,
        "timeout": (3, 20),
    }

    if data:
        request_args["data"] = data

    if tls:
        request_args["cert"] = (docker.client_cert, docker.client_key)
        request_args["verify"] = docker.ca_cert

    logging.info("Request to Docker: %s %s", request_args["method"], request_args["url"])

    resp = None
    try:
        # Timeout is set in request_args above
        resp = requests.request(**request_args)
    except ConnectionError:
        logging.error("Failed to establish a new connection. Connection refused.")
    except Timeout:
        logging.error("Request timed out.")
    except RequestException as err:
        logging.error("An error occurred while making the request: %s", err)

    return resp


# For the Docker Config Page. Gets the Current Repositories available on the Docker Server.
def get_repositories(
    docker: DockerConfig, tags: bool = False, repos: list[str] | str | None = None
) -> list[str]:
    """
    Retrieve list of Docker images/repositories available on Docker host.

    Args:
        docker: DockerConfig instance with API connection details
        tags: If True, return full image tags (e.g., "nginx:latest"). If False, return only repository names (e.g., "nginx")
        repos: Optional filter - only return images matching these repository names. Can be list or comma-separated string

    Returns:
        List of unique image names or tags. Returns empty list if Docker API is unreachable.
    """
    r = do_request(docker, "/images/json?all=1")

    if not r:
        return []

    # Convert repos to list if it's a comma-separated string
    repos_list: list[str] | None = None
    if repos:
        repos_list = repos.split(",") if isinstance(repos, str) else repos

    result = []
    for image in r.json():
        repo_tags = image.get("RepoTags")
        if not repo_tags:
            continue
        image_name, _ = repo_tags[0].split(":")
        if image_name == "<none>":
            continue

        if repos_list and image_name not in repos_list:
            continue
        else:
            result.append(image_name if not tags else repo_tags[0])

    return list(set(result))


def get_docker_info(docker: DockerConfig) -> str:
    """
    Retrieve Docker version and component information.

    Args:
        docker: DockerConfig instance with API connection details

    Returns:
        Formatted string containing Docker version, OS, and component details.
        Returns error message if Docker API is unreachable.
    """
    r = do_request(docker, "/version")

    if not r:
        return "Failed to get docker version info"

    response = r.json()
    components = response.get("Components")
    if not components:
        return "Failed to find information required in response."

    output = "Docker versions:\n"
    for component in components:
        output += f"{component['Name']}: {component['Version']}\n"

    return output


def is_swarm_mode(docker: DockerConfig) -> bool:
    """
    Check if Docker is running in swarm mode.

    Args:
        docker: DockerConfig instance

    Returns:
        True if swarm mode is active, False otherwise
    """
    r = do_request(docker, "/secrets")
    if not r:
        return False

    response_data = r.json()

    # If response is a dict with "message" key, Docker is not in swarm mode
    if isinstance(response_data, dict) and "message" in response_data:
        return False

    return True


def get_secrets(docker: DockerConfig) -> list[dict[str, str]]:
    """
    Retrieve list of Docker secrets from swarm.

    Args:
        docker: DockerConfig instance with API connection details

    Returns:
        List of secret dictionaries with 'ID' and 'Name' keys.
        Returns empty list if Docker is not in swarm mode.
    """
    r = do_request(docker, "/secrets")
    if not r:
        return []

    response_data = r.json()

    # Handle error responses (e.g., when Docker is not in swarm mode)
    if isinstance(response_data, dict) and "message" in response_data:
        return []

    secrets_list = []
    for secret in response_data:
        secret_dict = {
            "ID": secret["ID"],
            "Name": secret["Spec"]["Name"],
        }
        secrets_list.append(secret_dict)
    return secrets_list


def create_secret(docker: DockerConfig, name: str, data: str) -> tuple[str | None, bool]:
    """
    Create a Docker secret with base64-encoded data.

    Args:
        docker: DockerConfig instance with API connection details
        name: Secret name (must be unique)
        data: Secret value in plaintext (will be base64-encoded)

    Returns:
        Tuple of (secret_id, success_bool)
        - (secret_id, True) on successful creation
        - (None, False) on failure (name conflict, connection error, etc.)
    """
    # Base64 encode data server-side for integrity
    encoded_data = base64.b64encode(data.encode("utf-8")).decode("utf-8")

    # Build payload matching Docker Secrets API specification
    payload = json.dumps({"Name": name, "Data": encoded_data, "Labels": {}})

    # POST to /secrets/create endpoint
    r = do_request(docker, "/secrets/create", method="POST", data=payload)

    # Handle responses
    if not r:
        logging.error("Failed to contact Docker API for secret creation")
        return None, False

    if r.status_code == 201:
        # Success - extract ID from response
        secret_id = r.json().get("ID")
        logging.info("Successfully created secret '%s' with ID %s", name, secret_id)
        return secret_id, True
    elif r.status_code == 409:
        # Name conflict - log and return failure
        logging.warning("Secret name '%s' already exists", name)
        return None, False
    else:
        # Other errors - redact response if it contains secret data
        error_message = r.text
        if "Data" in error_message or "base64" in error_message:
            error_message = "[REDACTED - contains secret data]"
        logging.error("Failed to create secret '%s': %s - %s", name, r.status_code, error_message)
        return None, False


def delete_secret(docker: DockerConfig, secret_id: str) -> bool:
    """
    Delete a Docker secret by ID.

    Args:
        docker: DockerConfig instance
        secret_id: Docker secret ID to delete

    Returns:
        True if deletion succeeded, False otherwise

    Note:
        Docker returns 409 if secret is in use by a service.
        This function lets Docker handle that check (no pre-validation).
    """
    r = do_request(docker, f"/secrets/{secret_id}", method="DELETE")

    if not r:
        logging.error("Failed to contact Docker API for secret deletion: %s", secret_id)
        return False

    if r.ok:  # 204 No Content
        logging.info("Successfully deleted secret %s", secret_id)
        return True
    elif r.status_code == 409:
        # Secret in use - Docker provides message
        logging.warning("Cannot delete secret %s: %s", secret_id, r.json().get("message", "in use"))
        return False
    else:
        logging.error("Failed to delete secret %s: %s", secret_id, r.status_code)
        return False


def _extract_container_ports(containers_json: list[dict]) -> list[int]:
    """Extract public ports from container list."""
    result = []
    for container in containers_json:
        ports = container.get("Ports")
        if not ports:
            continue

        for port in ports:
            if port.get("PublicPort", 0):
                result.append(port["PublicPort"])

    return result


def _extract_service_ports(services_json: list[dict]) -> list[int]:
    """Extract published ports from service list."""
    result = []
    for service in services_json:
        endpoint = service.get("Endpoint", {}).get("Spec")
        if not endpoint:
            continue

        for port in endpoint.get("Ports", []):
            if pub_port := port.get("PublishedPort"):
                result.append(pub_port)

    return result


def get_unavailable_ports(docker: DockerConfig) -> list[int]:
    """Get list of ports already in use by containers and services."""
    # Get container ports
    r = do_request(docker, "/containers/json?all=1")
    if not r:
        logging.error("Unable to get list of ports that are unavailable (containers)!")
        return []

    result = _extract_container_ports(r.json())

    # Get service ports
    r = do_request(docker, "/services?all=1")
    if not r:
        logging.error("Unable to get list of ports that are unavailable (services)!")
        return result

    rj = r.json()
    if isinstance(rj, dict) and "This node is not a swarm manager." in rj.get("message"):
        return result

    result.extend(_extract_service_ports(rj))
    return result


def get_required_ports(
    docker: DockerConfig, image: str, challenge_ports: str | None = None
) -> list[str]:
    """
    Get required ports for a challenge, merging image metadata and challenge configuration.

    Args:
        docker: DockerConfig object
        image: Docker image name
        challenge_ports: Optional comma-separated string of ports (e.g., "80/tcp,443/tcp")

    Returns:
        List of port specifications (e.g., ["80/tcp", "443/tcp"])
    """
    ports = set()

    # Get ports from image metadata
    r = do_request(docker, f"/images/{image}/json?all=1")
    if r and hasattr(r, "json"):
        config = r.json().get("Config", {})
        exposed_ports = config.get("ExposedPorts")
        if exposed_ports:
            ports.update(exposed_ports.keys())

    # Merge with challenge-configured ports
    if challenge_ports and challenge_ports.strip():
        configured = [p.strip() for p in challenge_ports.split(",") if p.strip()]
        ports.update(configured)

    return list(ports)


def get_user_container(
    user: Any, team: Any, challenge: Any, *, is_teams: bool
) -> DockerChallengeTracker | None:
    """
    Get the Docker container/service for the current user or team.

    Args:
        user: User object
        team: Team object (or None)
        challenge: Challenge object with docker_image attribute
        is_teams: Whether CTFd is in teams mode

    Returns:
        DockerChallengeTracker instance if found, None otherwise
    """
    from ..models.models import DockerChallengeTracker as _Tracker

    query = _Tracker.query.filter_by(
        docker_image=challenge.docker_image,
        challenge_id=challenge.id,
    )

    if is_teams:
        return query.filter_by(team_id=team.id).first()
    else:
        return query.filter_by(user_id=user.id).first()


def cleanup_container_on_solve(
    docker: DockerConfig,
    user: Any,
    team: Any,
    challenge: Any,
    delete_func: Callable[[DockerConfig, str], bool],
    *,
    is_teams: bool,
) -> None:
    """
    Delete user's container/service when challenge is solved.

    Args:
        docker: DockerConfig instance
        user: User object
        team: Team object (or None)
        challenge: Challenge object
        delete_func: Function to call for deletion (delete_container or delete_service)
        is_teams: Whether CTFd is in teams mode
    """
    from ..models.models import DockerChallengeTracker as _Tracker

    container = get_user_container(user, team, challenge, is_teams=is_teams)
    if container:
        delete_func(docker, container.instance_id)
        _Tracker.query.filter_by(instance_id=container.instance_id).delete()
