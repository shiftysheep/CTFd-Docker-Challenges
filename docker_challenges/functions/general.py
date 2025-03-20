import logging
import requests
from requests import Response
from requests.exceptions import RequestException, Timeout

from ..models.models import DockerConfig

logger = logging.getLogger(__name__)


def do_request(
        docker: DockerConfig,
        url: str,
        headers: dict = None,
        method: str = "GET", 
        data: dict | str = None
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
        'url': f"{base}{url}",
        'headers': headers,
        'method': method,
        'timeout': (3, 20)
    }

    if data:
        request_args['data'] = data

    if tls:
        request_args['cert'] = (docker.client_cert, docker.client_key)
        request_args['verify'] = docker.ca_cert

    logging.info(f'Request to Docker: {request_args["method"]} {request_args["url"]}')

    resp = []
    try:
        resp = requests.request(**request_args)
    except ConnectionError:
        logging.error("Failed to establish a new connection. Connection refused.")
    except Timeout:
        logging.error("Request timed out.")
    except RequestException as err:
        logging.error(f"An error occurred while making the request: {err}")

    return resp


# For the Docker Config Page. Gets the Current Repositories available on the Docker Server.
def get_repositories(docker: DockerConfig, tags=False, repos=False):
    r = do_request(docker, "/images/json?all=1")

    if not r:
        return []

    result = list()
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
        return 'Failed to get docker version info'

    response = r.json()
    components = response.get('Components')
    if not components:
        return 'Failed to find information required in response.'

    output = 'Docker versions:\n'
    for component in components:
        output += f"{component['Name']}: {component['Version']}\n"

    return output


def get_secrets(docker: DockerConfig):
    r = do_request(docker, "/secrets")
    tmplist = list()
    for secret in r.json():
        tmpdict = {}
        tmpdict["ID"] = secret["ID"]
        tmpdict["Name"] = secret["Spec"]["Name"]
        tmplist.append(tmpdict)
    return tmplist


def delete_secret(docker: DockerConfig, id: str):
    r = do_request(docker, f"/secrets/{id}", method="DELETE")
    return r.ok


def get_unavailable_ports(docker: DockerConfig):
    r = do_request(docker, "/containers/json?all=1")

    if not r:
        print('Unable to get list of ports that are unavailable (containers)!')
        return []

    result = list()
    for i in r.json():
        ports = i.get("Ports")
        if not ports:
            continue

        for port in ports:
            if port.get("PublicPort", 0):
                result.append(port["PublicPort"])

    r = do_request(docker, "/services?all=1")
    if not r:
        print('Unable to get list of ports that are unavailable (services)!')
        return result

    rj = r.json()
    if isinstance(rj, dict) and 'This node is not a swarm manager.' in rj.get("message"):
        return result

    for i in r.json():
        endpoint = i.get("Endpoint",{}).get("Spec")
        if not endpoint:
            continue

        for port in endpoint.get("Ports", []):
            if pub_port := port.get("PublishedPort"):
                result.append(pub_port)

    return result


def get_required_ports(docker, image):
    r = do_request(docker, f"/images/{image}/json?all=1")
    result = r.json()["Config"]["ExposedPorts"].keys()
    return result
