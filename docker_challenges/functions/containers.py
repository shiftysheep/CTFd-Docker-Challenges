import hashlib
import json
import random

from ..functions.general import do_request, get_required_ports
from ..models.models import DockerConfig


def find_existing(docker: DockerConfig, name: str):
    r = do_request(docker, url=f'/containers/json?all=1&filters={{"name":["{name}"]}}')

    if not r:
        print('Failed to contact Docker!')

    if len(r.json()) == 1:
        return r.json()[0]['Id']


def create_container(docker: DockerConfig, image: str, team, portbl: list):
    needed_ports = get_required_ports(docker, image)
    team = hashlib.md5(team.encode("utf-8")).hexdigest()[:10]
    container_name = "%s_%s" % (image.replace(':', '_').replace('/', '_').replace('.', '_'), team)
    assigned_ports = dict()

    for i in needed_ports:
        while True:
            assigned_port = random.choice(range(30000, 60000))
            if assigned_port not in portbl:
                assigned_ports['%s/tcp' % assigned_port] = {}
                break

    ports = dict()
    bindings = dict()
    tmp_ports = list(assigned_ports.keys())
    for i in needed_ports:
        ports[i] = {}
        bindings[i] = [{"HostPort": tmp_ports.pop()}]
    data = json.dumps({"Image": image, "ExposedPorts": ports, "HostConfig": {"PortBindings": bindings}})

    r = do_request(docker, url=f"/containers/create?name={container_name}", method="POST", data=data)
    if r.status_code == 409:
        instance_id = find_existing(docker, container_name)
    else:
        instance_id = r.json()['Id']

    do_request(docker, url=f"/containers/{instance_id}/start", method="POST")

    return instance_id, data


def delete_container(docker, instance_id):
    r = do_request(docker, f'/containers/{instance_id}?force=true', method='DELETE')
    return r.ok
