import hashlib
import json
import random

from ..functions.general import do_request, get_required_ports


def create_container(docker, image, team, portbl):
    needed_ports = get_required_ports(docker, image)
    team = hashlib.md5(team.encode("utf-8")).hexdigest()[:10]
    container_name = "%s_%s" % (image.split(':')[1], team)
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
    result = r.json()
    s = do_request(docker, url=f"/containers/{result['Id']}/start", method="POST")
    return result, data


def delete_container(docker, instance_id):
    do_request(docker, f'/containers/{instance_id}?force=true', method='DELETE')
    return True