import hashlib
import json
import random

from ..constants import (
    MAX_PORT_ASSIGNMENT_ATTEMPTS,
    PORT_ASSIGNMENT_MAX,
    PORT_ASSIGNMENT_MIN,
)
from ..functions.general import do_request, get_required_ports
from ..models.models import DockerConfig


def find_existing(docker: DockerConfig, name: str):
    r = do_request(docker, url=f'/containers/json?all=1&filters={{"name":["{name}"]}}')

    if not r:
        print("Failed to contact Docker!")

    if len(r.json()) == 1:
        return r.json()[0]["Id"]


def create_container(docker: DockerConfig, image: str, team, portbl: list, exposed_ports=None):
    needed_ports = get_required_ports(docker, image, exposed_ports)
    # MD5 used for container naming only, not security
    team = hashlib.md5(team.encode("utf-8")).hexdigest()[:10]  # noqa: S324
    container_name = "{}_{}".format(
        image.replace(":", "_").replace("/", "_").replace(".", "_"),
        team,
    )
    assigned_ports = {}

    for _i in needed_ports:
        assigned_port = None
        for _attempt in range(MAX_PORT_ASSIGNMENT_ATTEMPTS):
            # random.choice used for port assignment, not cryptographic purposes
            candidate_port = random.choice(range(PORT_ASSIGNMENT_MIN, PORT_ASSIGNMENT_MAX))  # noqa: S311
            if candidate_port not in portbl:
                assigned_port = candidate_port
                assigned_ports[f"{assigned_port}/tcp"] = {}
                break

        if assigned_port is None:
            raise RuntimeError(
                f"Failed to find available port after {MAX_PORT_ASSIGNMENT_ATTEMPTS} attempts. "
                f"Port range {PORT_ASSIGNMENT_MIN}-{PORT_ASSIGNMENT_MAX} may be exhausted."
            )

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
    instance_id = find_existing(docker, container_name) if r.status_code == 409 else r.json()["Id"]

    do_request(docker, url=f"/containers/{instance_id}/start", method="POST")

    return instance_id, data


def delete_container(docker, instance_id):
    r = do_request(docker, f"/containers/{instance_id}?force=true", method="DELETE")
    return r.ok
