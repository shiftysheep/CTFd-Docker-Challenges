import logging
import re

from CTFd.models import (
    ChallengeFiles,
    Challenges,
    Fails,
    Flags,
    Hints,
    Solves,
    Tags,
    db,
)
from CTFd.plugins.challenges import BaseChallenge, ChallengeResponse
from CTFd.plugins.flags import get_flag_class
from CTFd.utils.config import is_teams_mode
from CTFd.utils.uploads import delete_file
from CTFd.utils.user import get_ip
from flask import Blueprint

from ..functions.services import delete_service
from ..models.models import DockerChallengeTracker, DockerConfig, DockerServiceChallenge


def _validate_exposed_ports(ports_string):
    """
    Validate exposed ports format and values.

    Args:
        ports_string: Comma-separated string of ports (e.g., "80/tcp,443/tcp,53/udp")

    Raises:
        ValueError: If validation fails with descriptive error message
    """
    if not ports_string or not ports_string.strip():
        raise ValueError(
            "At least one exposed port must be configured. "
            "Please add a port in the format: port/protocol (e.g., 80/tcp)"
        )

    # Pattern matches: port/protocol where port is 1-65535, protocol is tcp/udp
    port_pattern = re.compile(r"^(\d+)/(tcp|udp)$", re.IGNORECASE)

    ports = ports_string.split(",")
    valid_ports = []

    for port_str in ports:
        port_str = port_str.strip()
        if not port_str:
            continue

        match = port_pattern.match(port_str)
        if not match:
            raise ValueError(
                f"Invalid port format: '{port_str}'. "
                "Expected format: port/protocol (e.g., 80/tcp, 443/tcp, 53/udp)"
            )

        port_num = int(match.group(1))
        if port_num < 1 or port_num > 65535:
            raise ValueError(
                f"Port number {port_num} is out of valid range. "
                "Port numbers must be between 1 and 65535."
            )

        valid_ports.append(port_str)

    if not valid_ports:
        raise ValueError(
            "At least one valid port must be configured. "
            "Ports must be in the format: port/protocol (e.g., 80/tcp)"
        )


class DockerServiceChallengeType(BaseChallenge):
    id = "docker_service"
    name = "docker_service"
    templates = {
        "create": "/plugins/docker_challenges/assets/create_service.html",
        "update": "/plugins/docker_challenges/assets/update_service.html",
        "view": "/plugins/docker_challenges/assets/view.html",
    }
    scripts = {
        "create": "/plugins/docker_challenges/assets/create_service.js",
        "update": "/plugins/docker_challenges/assets/update_service.js",
        "view": "/plugins/docker_challenges/assets/view.js",
    }
    route = "/plugins/docker_challenges/assets"
    blueprint = Blueprint(
        "docker_service_challenges",
        __name__,
        template_folder="templates",
        static_folder="assets",
    )

    @staticmethod
    def update(challenge, request):
        """
        This method is used to update the information associated with a challenge. This should be kept strictly to the
        Challenges table and any child tables.

        :param challenge:
        :param request:
        :return:
        """
        data = request.form or request.get_json()
        existing = DockerServiceChallenge.query.filter_by(
            id=challenge.id
        ).first()  # Adding to protect patches from removing configuration
        data["protect_secrets"] = bool(int(data.get("protect_secrets", existing.protect_secrets)))
        data["docker_secrets"] = data.get("docker_secrets_array", existing.docker_secrets)
        data["docker_type"] = "service"
        if data.get("docker_secrets_array", None):
            del data["docker_secrets_array"]

        # Validate exposed_ports if present in the update
        if "exposed_ports" in data:
            try:
                _validate_exposed_ports(data["exposed_ports"])
            except ValueError as e:
                raise ValueError(f"Port validation failed: {str(e)}") from e

        for attr, value in data.items():
            setattr(challenge, attr, value)

        db.session.commit()
        return challenge

    @staticmethod
    def delete(challenge):
        """
        This method is used to delete the resources used by a challenge.
        NOTE: Will need to kill all containers here

        :param challenge:
        :return:
        """
        Fails.query.filter_by(challenge_id=challenge.id).delete()
        Solves.query.filter_by(challenge_id=challenge.id).delete()
        Flags.query.filter_by(challenge_id=challenge.id).delete()
        files = ChallengeFiles.query.filter_by(challenge_id=challenge.id).all()
        for f in files:
            delete_file(f.id)
        ChallengeFiles.query.filter_by(challenge_id=challenge.id).delete()
        Tags.query.filter_by(challenge_id=challenge.id).delete()
        Hints.query.filter_by(challenge_id=challenge.id).delete()
        DockerServiceChallenge.query.filter_by(id=challenge.id).delete()
        Challenges.query.filter_by(id=challenge.id).delete()
        db.session.commit()

    @staticmethod
    def read(challenge):
        """
        This method is in used to access the data of a challenge in a format processable by the front end.

        :param challenge:
        :return: Challenge object, data dictionary to be returned to the user
        """
        challenge = DockerServiceChallenge.query.filter_by(id=challenge.id).first()
        data = {
            "id": challenge.id,
            "name": challenge.name,
            "value": challenge.value,
            "docker_image": challenge.docker_image,
            "exposed_ports": challenge.exposed_ports,
            "description": challenge.description,
            "category": challenge.category,
            "secrets": challenge.docker_secrets.split(","),
            "state": challenge.state,
            "max_attempts": challenge.max_attempts,
            "type": challenge.type,
            "type_data": {
                "id": DockerServiceChallengeType.id,
                "name": DockerServiceChallengeType.name,
                "templates": DockerServiceChallengeType.templates,
                "scripts": DockerServiceChallengeType.scripts,
            },
        }
        return data

    @staticmethod
    def create(request):
        """
        This method is used to process the challenge creation request.

        :param request:
        :return:
        """
        data = request.form or request.get_json()
        data["protect_secrets"] = bool(int(data.get("protect_secrets", 0)))
        data["docker_secrets"] = data["docker_secrets_array"]
        data["docker_type"] = "service"
        del data["docker_secrets_array"]

        # Validate exposed_ports
        if "exposed_ports" in data:
            try:
                _validate_exposed_ports(data["exposed_ports"])
            except ValueError as e:
                raise ValueError(f"Port validation failed: {str(e)}") from e

        challenge = DockerServiceChallenge(**data)
        db.session.add(challenge)
        db.session.commit()
        return challenge

    @staticmethod
    def attempt(challenge, request):
        """
        This method is used to check whether a given input is right or wrong. It does not make any changes and should
        return a boolean for correctness and a string to be shown to the user. It is also in charge of parsing the
        user's input from the request itself.

        :param challenge: The Challenge object from the database
        :param request: The request the user submitted
        :return: (boolean, string)
        """

        data = request.form or request.get_json()
        print(request.get_json())
        print(data)
        submission = data["submission"].strip()
        flags = Flags.query.filter_by(challenge_id=challenge.id).all()
        for flag in flags:
            if get_flag_class(flag.type).compare(flag, submission):
                return ChallengeResponse(status="correct", message="Correct")
        return ChallengeResponse(status="incorrect", message="Incorrect")

    @staticmethod
    def solve(user, team, challenge, request):
        """
        This method is used to insert Solves into the database in order to mark a challenge as solved.

        :param team: The Team object from the database
        :param chal: The Challenge object from the database
        :param request: The request the user submitted
        :return:
        """
        data = request.form or request.get_json()
        submission = data["submission"].strip()
        docker = DockerConfig.query.filter_by(id=1).first()
        try:
            if is_teams_mode():
                docker_containers = (
                    DockerChallengeTracker.query.filter_by(docker_image=challenge.docker_image)
                    .filter_by(team_id=team.id)
                    .first()
                )
            else:
                docker_containers = (
                    DockerChallengeTracker.query.filter_by(docker_image=challenge.docker_image)
                    .filter_by(user_id=user.id)
                    .first()
                )
            delete_service(docker, docker_containers.instance_id)
            DockerChallengeTracker.query.filter_by(
                instance_id=docker_containers.instance_id
            ).delete()
        except Exception as e:
            # Service may have already been deleted or never created
            logging.debug(f"Failed to delete service on solve: {e}")
        solve = Solves(
            user_id=user.id,
            team_id=team.id if team else None,
            challenge_id=challenge.id,
            ip=get_ip(req=request),
            provided=submission,
        )
        db.session.add(solve)
        db.session.commit()
        # trying if this solves the detached instance error...
        # db.session.close()

    @staticmethod
    def fail(user, team, challenge, request):
        """
        This method is used to insert Fails into the database in order to mark an answer incorrect.

        :param team: The Team object from the database
        :param chal: The Challenge object from the database
        :param request: The request the user submitted
        :return:
        """
        data = request.form or request.get_json()
        submission = data["submission"].strip()
        wrong = Fails(
            user_id=user.id,
            team_id=team.id if team else None,
            challenge_id=challenge.id,
            ip=get_ip(request),
            provided=submission,
        )
        db.session.add(wrong)
        db.session.commit()
