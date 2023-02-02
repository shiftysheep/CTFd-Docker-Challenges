import hashlib
import json
import random

from ..functions.general import do_request, get_required_ports, get_secrets
from ..models.models import DockerConfig


def create_service(docker:DockerConfig, image:str, team:str, portbl:list):
    needed_ports = get_required_ports(docker, image)
    team = hashlib.md5(team.encode("utf-8")).hexdigest()[:10]
    service_name = f"svc_{image.split(':')[1]}{team}"
    assigned_ports = list()
    for i in needed_ports:
        tmpdict = {}
        while True:
            assigned_port = random.choice(range(30000, 60000))
            if assigned_port not in portbl:
                tmpdict['PublishedPort'] = assigned_port
                tmpdict['PublishMode'] = 'ingress'
                tmpdict['Protocol'] = 'tcp'
                tmpdict['TargetPort'] = i
                tmpdict['Name'] = f"Exposed Port {i}"
                assigned_ports.append(tmpdict)
                break
    secrets = get_service_secrets(docker, image)
    data = json.dumps(
        {
            "Name": service_name, 
            "TaskTemplate": {
                "ContainerSpec": {
                    "Image": image, 
                    "Secrets": [
                        {
                            "File": {
                                "Name": "/run/secrets/test_secret",
                                "UID": "1",
                                "GID": "1",
                                "Mode": 777
                            },
                            "SecretID": "p7dlutf8wk1ix92a1hu5xt0bm",
                            "SecretName": "test-secret"
                        }
                    ]
                }
            },
            "EndpointSpec": {
                "Mode": "vip",
                "Ports": assigned_ports
            }
        }
    )
    r = do_request(docker, url=f"/services/create?name={service_name}", method="POST", data=data)
    result = r.json()
    return result, data


def delete_service(docker:DockerConfig, instance_id:str) -> bool:
    do_request(docker, f'/services/{instance_id}', method='DELETE')
    return True