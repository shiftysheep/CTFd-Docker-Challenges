import json
from datetime import datetime

from CTFd.models import db
from CTFd.utils.config import is_teams_mode
from CTFd.utils.dates import unix_time
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.utils.user import get_current_team, get_current_user
from flask import abort, request
from flask_restx import Namespace, Resource

from ..functions.containers import create_container, delete_container
from ..functions.general import (
    get_repositories,
    get_required_ports,
    get_secrets,
    get_unavailable_ports,
)
from ..functions.services import create_service, delete_service
from ..models.models import (
    DockerChallenge,
    DockerChallengeTracker,
    DockerConfig,
    DockerServiceChallenge,
)

active_docker_namespace = Namespace(
    "docker_status", description="Endpoint to retrieve User Docker Image Status"
)
container_namespace = Namespace("container", description="Endpoint to interact with containers")
docker_namespace = Namespace("docker", description="Endpoint to retrieve dockerstuff")
secret_namespace = Namespace("secret", description="Endpoint to retrieve dockerstuff")
kill_container = Namespace("nuke", description="Endpoint to nuke containers")
image_ports_namespace = Namespace(
    "image_ports", description="Endpoint to retrieve image exposed ports"
)


def delete_docker(docker, docker_type, instance_id):
    """Delete a Docker container or service and remove from tracker."""
    if docker_type == "docker_service":
        assert delete_service(docker, instance_id)
    else:
        assert delete_container(docker, instance_id)
    DockerChallengeTracker.query.filter_by(instance_id=instance_id).delete()
    db.session.commit()


def _cleanup_stale_containers(docker, session, is_teams):
    """Clean up containers older than 2 hours for current session."""
    containers = DockerChallengeTracker.query.all()
    session_id_field = "team_id" if is_teams else "user_id"

    for container in containers:
        session_id = getattr(container, session_id_field)
        age_seconds = unix_time(datetime.utcnow()) - int(container.timestamp)

        if int(session.id) == int(session_id) and age_seconds >= 7200:
            challenge = DockerChallenge.query.filter_by(id=container.challenge_id).first()
            if not challenge:
                challenge = DockerServiceChallenge.query.filter_by(
                    id=container.challenge_id
                ).first()

            if challenge:
                delete_docker(docker, challenge.type, container.instance_id)


def _get_existing_container(session, challenge, is_teams):
    """Get existing container for session and challenge if it exists."""
    query = DockerChallengeTracker.query
    query = query.filter_by(team_id=session.id) if is_teams else query.filter_by(user_id=session.id)

    return (
        query.filter_by(docker_image=challenge.docker_image)
        .filter_by(challenge_id=challenge.id)
        .first()
    )


def _should_revert_container(existing_container):
    """Check if container should be reverted (older than 5 minutes)."""
    if not existing_container:
        return False

    age_seconds = unix_time(datetime.utcnow()) - int(existing_container.timestamp)
    return age_seconds >= 300


def _get_challenge_by_id(challenge_id):
    """Retrieve challenge by ID, checking both Docker and DockerService types."""
    challenge = DockerChallenge.query.filter_by(id=challenge_id).first()
    if not challenge:
        challenge = DockerServiceChallenge.query.filter_by(id=challenge_id).first()
    return challenge


def _create_docker_instance(docker, challenge, session, portsbl):
    """Create a new Docker container or service instance."""
    if challenge.docker_type == "service":
        instance_id, data = create_service(
            docker,
            challenge_id=challenge.id,
            image=challenge.docker_image,
            team=session.name,
            portbl=portsbl,
        )
        if not instance_id:
            return None, None, None

        ports_json = json.loads(data)["EndpointSpec"]["Ports"]
        ports = [f"{p['PublishedPort']}/{p['Protocol']}-> {p['TargetPort']}" for p in ports_json]
    else:
        instance_id, data = create_container(
            docker, challenge.docker_image, session.name, portsbl, challenge.exposed_ports
        )
        ports_json = json.loads(data)["HostConfig"]["PortBindings"]
        ports = [f"{values[0]['HostPort']}->{target}" for target, values in ports_json.items()]

    return instance_id, ports, data


def _handle_container_creation(docker, challenge, session, is_teams):
    """Handle complete container/service creation workflow."""
    # Clean up stale containers (older than 2 hours)
    _cleanup_stale_containers(docker, session, is_teams)

    # Check for existing container
    existing = _get_existing_container(session, challenge, is_teams)

    # Don't create if container exists and is less than 5 minutes old
    if existing and not _should_revert_container(existing):
        return None

    # Revert container if it exists and is old enough
    if existing:
        delete_docker(docker, challenge.type, existing.instance_id)

    # Create new container/service
    portsbl = get_unavailable_ports(docker)
    instance_id, ports, _data = _create_docker_instance(docker, challenge, session, portsbl)

    return (instance_id, ports) if instance_id else None


def _get_all_challenges():
    """Get all challenges indexed by ID."""
    challenges = {c.id: c for c in DockerChallenge.query.all()}
    challenges.update({c.id: c for c in DockerServiceChallenge.query.all()})
    return challenges


def _kill_all_containers(docker_config, docker_tracker, challenges):
    """Kill all tracked containers."""
    for tracker_entry in docker_tracker:
        challenge = challenges.get(tracker_entry.challenge_id)
        if challenge:
            print(f"type:{challenge.type}")
            print(f"instance_id:{tracker_entry.instance_id}")
            delete_docker(
                docker=docker_config,
                docker_type=challenge.type,
                instance_id=tracker_entry.instance_id,
            )


def _kill_single_container(docker_config, container_id, docker_tracker, challenges):
    """Kill a specific container by ID."""
    tracker_entry = next((c for c in docker_tracker if c.instance_id == container_id), None)
    if not tracker_entry:
        return "Container not found", 404

    challenge = challenges.get(tracker_entry.challenge_id)
    if not challenge:
        return "Challenge not found", 404

    delete_docker(
        docker=docker_config, docker_type=challenge.type, instance_id=tracker_entry.instance_id
    )
    return None


@kill_container.route("", methods=["POST", "GET"])
class KillContainerAPI(Resource):
    @admins_only
    def get(self):
        container = request.args.get("container")
        full = request.args.get("all")
        docker_config = DockerConfig.query.filter_by(id=1).first_or_404()
        docker_tracker = DockerChallengeTracker.query.all()
        challenges = _get_all_challenges()

        if full == "true":
            _kill_all_containers(docker_config, docker_tracker, challenges)
        elif (
            container
            and container != "null"
            and container in [c.instance_id for c in docker_tracker]
        ):
            error = _kill_single_container(docker_config, container, docker_tracker, challenges)
            if error:
                return error
        else:
            return "Invalid request", 400

        return "Success", 200


@container_namespace.route("", methods=["POST", "GET"])
class ContainerAPI(Resource):
    @authed_only
    # I wish this was Post... Issues with API/CSRF and whatnot. Open to a Issue solving this.
    def get(self):
        challenge_id = request.args.get("id")
        if not challenge_id:
            return abort(403)

        # Get Docker config and challenge
        docker = DockerConfig.query.filter_by(id=1).first()
        challenge = _get_challenge_by_id(challenge_id)
        if not challenge:
            return abort(403)

        # Get current session (team or user)
        is_teams = is_teams_mode()
        session = get_current_team() if is_teams else get_current_user()

        # Handle container creation workflow
        result = _handle_container_creation(docker, challenge, session, is_teams)
        if not result:
            return abort(403) if result is None else abort(500)

        instance_id, ports = result

        # Track the new container
        entry = DockerChallengeTracker(
            team_id=session.id if is_teams else None,
            user_id=session.id if not is_teams else None,
            challenge_id=challenge_id,
            docker_image=challenge.docker_image,
            timestamp=unix_time(datetime.utcnow()),
            revert_time=unix_time(datetime.utcnow()) + 300,
            instance_id=instance_id,
            ports=",".join(ports),
            host=str(docker.hostname).split(":")[0],
        )
        db.session.add(entry)
        db.session.commit()
        return


@active_docker_namespace.route("", methods=["POST", "GET"])
class DockerStatus(Resource):
    """
    The Purpose of this API is to retrieve a public JSON string of all docker containers
    in use by the current team/user.
    """

    @authed_only
    def get(self):
        docker = DockerConfig.query.filter_by(id=1).first()
        if is_teams_mode():
            session = get_current_team()
            tracker = DockerChallengeTracker.query.filter_by(team_id=session.id)
        else:
            session = get_current_user()
            tracker = DockerChallengeTracker.query.filter_by(user_id=session.id)
        data = []
        for i in tracker:
            data.append(
                {
                    "id": i.id,
                    "team_id": i.team_id,
                    "user_id": i.user_id,
                    "challenge_id": i.challenge_id,
                    "docker_image": i.docker_image,
                    "timestamp": i.timestamp,
                    "revert_time": i.revert_time,
                    "instance_id": i.instance_id,
                    "ports": i.ports.split(","),
                    "host": str(docker.hostname).split(":")[0],
                }
            )
        return {"success": True, "data": data}


@docker_namespace.route("", methods=["POST", "GET"])
class DockerAPI(Resource):
    """
    This is for creating Docker Challenges. The purpose of this API is to populate the Docker Image Select form
    object in the Challenge Creation Screen.
    """

    @admins_only
    def get(self):
        docker = DockerConfig.query.filter_by(id=1).first()
        images = get_repositories(docker, tags=True, repos=docker.repositories)
        if images:
            data = []
            for i in images:
                data.append({"name": i})
            return {"success": True, "data": data}
        return {"success": False, "data": [{"name": "Error in Docker Config!"}]}, 400


@secret_namespace.route("", methods=["POST", "GET"])
class SecretAPI(Resource):
    """
    This is for creating Docker Challenges. The purpose of this API is to populate the Docker Secret Select form
    object in the Challenge Creation Screen.
    """

    @admins_only
    def get(self):
        docker = DockerConfig.query.filter_by(id=1).first()
        secrets = get_secrets(docker)
        if secrets:
            data = []
            for i in secrets:
                data.append({"name": i["Name"], "id": i["ID"]})
            return {"success": True, "data": data}
        return {"success": False, "data": [{"name": "Error in Docker Config!"}]}, 400


@image_ports_namespace.route("", methods=["GET"])
class ImagePortsAPI(Resource):
    """
    This endpoint retrieves the exposed ports from a Docker image's metadata.
    Used to auto-populate the exposed_ports field in challenge creation forms.
    """

    @admins_only
    def get(self):
        import logging
        import traceback

        image = request.args.get("image")
        if not image:
            return {"success": False, "error": "Image parameter required"}, 400

        docker = DockerConfig.query.filter_by(id=1).first()
        if not docker:
            return {"success": False, "error": "Docker config not found"}, 404

        try:
            ports = get_required_ports(docker, image, challenge_ports=None)
            return {"success": True, "ports": ports}
        except Exception as e:
            logging.error(f"Error in image_ports endpoint: {type(e).__name__}: {e}")
            logging.error(f"Traceback: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}, 500
