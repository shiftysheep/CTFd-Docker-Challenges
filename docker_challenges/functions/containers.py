import hashlib
import json
import random

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
        while True:
            # random.choice used for port assignment, not cryptographic purposes
            assigned_port = random.choice(range(30000, 60000))  # noqa: S311
            if assigned_port not in portbl:
                assigned_ports[f"{assigned_port}/tcp"] = {}
                break

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
