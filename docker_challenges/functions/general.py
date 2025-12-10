import logging

import requests
from requests import Response
from requests.exceptions import RequestException, Timeout

from ..models.models import DockerChallengeTracker, DockerConfig


def do_request(
    docker: DockerConfig,
    url: str,
    headers: dict[str, str] | None = None,
    method: str = "GET",
    data: dict | str | None = None,
) -> list | Response:
    tls = docker.tls_enabled
    prefix = "https" if tls else "http"
    host = docker.hostname
    base = f"{prefix}://{host}"

    # If no host set, request will fail
    if not host:
        return []

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

    logging.info(f"Request to Docker: {request_args['method']} {request_args['url']}")

    resp = []
    try:
        # Timeout is set in request_args above
        resp = requests.request(**request_args)  # noqa: S113
    except ConnectionError:
        logging.error("Failed to establish a new connection. Connection refused.")
    except Timeout:
        logging.error("Request timed out.")
    except RequestException as err:
        logging.error(f"An error occurred while making the request: {err}")

    return resp


# For the Docker Config Page. Gets the Current Repositories available on the Docker Server.
def get_repositories(
    docker: DockerConfig, tags: bool = False, repos: bool | list = False
) -> list[str]:
    r = do_request(docker, "/images/json?all=1")

    if not r:
        return []

    result = []
    for image in r.json():
        repo_tags = image.get("RepoTags")
        if not repo_tags:
            continue
        image_name, _ = repo_tags[0].split(":")
        if image_name == "<none>":
            continue

        if repos and image_name not in repos:
            continue
        else:
            result.append(image_name if not tags else repo_tags[0])

    return list(set(result))


def get_docker_info(docker: DockerConfig) -> str:
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


def get_secrets(docker: DockerConfig) -> list[dict[str, str]]:
    r = do_request(docker, "/secrets")
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


def get_user_container(user, team, challenge) -> DockerChallengeTracker | None:
    """
    Get the Docker container/service for the current user or team.

    Args:
        user: User object
        team: Team object (or None)
        challenge: Challenge object with docker_image attribute

    Returns:
        DockerChallengeTracker instance if found, None otherwise
    """
    from CTFd.utils.config import is_teams_mode

    query = DockerChallengeTracker.query.filter_by(docker_image=challenge.docker_image)

    if is_teams_mode():
        return query.filter_by(team_id=team.id).first()
    else:
        return query.filter_by(user_id=user.id).first()


def cleanup_container_on_solve(docker: DockerConfig, user, team, challenge, delete_func) -> None:
    """
    Delete user's container/service when challenge is solved.

    Args:
        docker: DockerConfig instance
        user: User object
        team: Team object (or None)
        challenge: Challenge object
        delete_func: Function to call for deletion (delete_container or delete_service)
    """
    container = get_user_container(user, team, challenge)
    if container:
        delete_func(docker, container.instance_id)
        DockerChallengeTracker.query.filter_by(instance_id=container.instance_id).delete()
