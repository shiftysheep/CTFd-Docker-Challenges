import hashlib
import json
import random

from ..functions.general import do_request, get_required_ports, get_secrets
from ..models.models import DockerConfig, DockerServiceChallenge


def create_service(docker: DockerConfig, challenge_id: int, image: str, team: str, portbl: list):
    challenge = DockerServiceChallenge.query.filter_by(id=challenge_id).first()
    exposed_ports = challenge.exposed_ports if challenge else None
    needed_ports = get_required_ports(docker, image, exposed_ports)
    # MD5 used for service naming only, not security
    team = hashlib.md5(team.encode("utf-8")).hexdigest()[:10]  # noqa: S324
    service_name = f"svc_{image.split(':')[1]}{team}"
    assigned_ports = []
    for _i in needed_ports:
        tmpdict = {}
        while True:
            # random.choice used for port assignment, not cryptographic purposes
            assigned_port = random.choice(range(30000, 60000))  # noqa: S311
            if assigned_port not in portbl:
                tmpdict["PublishedPort"] = assigned_port
                tmpdict["PublishMode"] = "ingress"
                tmpdict["Protocol"] = "tcp"
                tmpdict["TargetPort"] = int(_i.split("/")[0])
                tmpdict["Name"] = f"Exposed Port {_i}"
                assigned_ports.append(tmpdict)
                break
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
    data = json.dumps(
        {
            "Name": service_name,
            "TaskTemplate": {"ContainerSpec": {"Image": image, "Secrets": secrets_list}},
            "EndpointSpec": {"Mode": "vip", "Ports": assigned_ports},
        }
    )
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
