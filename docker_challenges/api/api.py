import json
import logging
import re
import traceback
from datetime import datetime
from typing import Any

from CTFd.models import db
from CTFd.utils.config import is_teams_mode
from CTFd.utils.dates import unix_time
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.utils.user import get_current_team, get_current_user
from flask import request
from flask_restx import Namespace, Resource

from ..constants import CONTAINER_REVERT_TIMEOUT_SECONDS, CONTAINER_STALE_TIMEOUT_SECONDS
from ..functions.containers import create_container, delete_container
from ..functions.general import (
    create_secret,
    delete_secret,
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


def delete_docker(docker: DockerConfig, docker_type: str, instance_id: str) -> None:
    """Delete a Docker container or service and remove from tracker."""
    if docker_type == "docker_service":
        if not delete_service(docker, instance_id):
            raise RuntimeError(f"Failed to delete Docker service: {instance_id}")
    else:
        if not delete_container(docker, instance_id):
            raise RuntimeError(f"Failed to delete Docker container: {instance_id}")
    DockerChallengeTracker.query.filter_by(instance_id=instance_id).delete()
    db.session.commit()


def _cleanup_stale_containers(docker: DockerConfig, session: Any, is_teams: bool) -> None:
    """Clean up containers older than CONTAINER_STALE_TIMEOUT_SECONDS for current session."""
    # Calculate stale timestamp threshold
    current_time = unix_time(datetime.utcnow())
    stale_threshold = current_time - CONTAINER_STALE_TIMEOUT_SECONDS

    # Filter at database level: only query current session's stale containers
    query = DockerChallengeTracker.query
    query = query.filter_by(team_id=session.id) if is_teams else query.filter_by(user_id=session.id)

    # Further filter by timestamp at database level
    containers = query.filter(DockerChallengeTracker.timestamp <= str(stale_threshold)).all()

    for container in containers:
        challenge = DockerChallenge.query.filter_by(id=container.challenge_id).first()
        if not challenge:
            challenge = DockerServiceChallenge.query.filter_by(id=container.challenge_id).first()

        if challenge:
            delete_docker(docker, challenge.type, container.instance_id)


def _get_existing_container(
    session: Any, challenge: DockerChallenge | DockerServiceChallenge, is_teams: bool
) -> DockerChallengeTracker | None:
    """Get existing container for session and challenge if it exists."""
    query = DockerChallengeTracker.query
    query = query.filter_by(team_id=session.id) if is_teams else query.filter_by(user_id=session.id)

    return (
        query.filter_by(docker_image=challenge.docker_image)
        .filter_by(challenge_id=challenge.id)
        .first()
    )


def _should_revert_container(existing_container: DockerChallengeTracker | None) -> bool:
    """Check if container should be reverted (older than CONTAINER_REVERT_TIMEOUT_SECONDS)."""
    if not existing_container:
        return False

    age_seconds = unix_time(datetime.utcnow()) - int(existing_container.timestamp)
    return age_seconds >= CONTAINER_REVERT_TIMEOUT_SECONDS


def _get_challenge_by_id(challenge_id: int) -> DockerChallenge | DockerServiceChallenge | None:
    """Retrieve challenge by ID, checking both Docker and DockerService types."""
    challenge = DockerChallenge.query.filter_by(id=challenge_id).first()
    if not challenge:
        challenge = DockerServiceChallenge.query.filter_by(id=challenge_id).first()
    return challenge


def _create_docker_instance(
    docker: DockerConfig,
    challenge: DockerChallenge | DockerServiceChallenge,
    session: Any,
    portsbl: list[int],
) -> tuple[str | None, list[str] | None, str | None]:
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


def _handle_container_creation(
    docker: DockerConfig,
    challenge: DockerChallenge | DockerServiceChallenge,
    session: Any,
    is_teams: bool,
) -> tuple[str, list[str]] | None:
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


def _get_all_challenges() -> dict[int, DockerChallenge | DockerServiceChallenge]:
    """Get all challenges indexed by ID."""
    challenges = {c.id: c for c in DockerChallenge.query.all()}
    challenges.update({c.id: c for c in DockerServiceChallenge.query.all()})
    return challenges


def _kill_all_containers(
    docker_config: DockerConfig,
    challenges: dict[int, DockerChallenge | DockerServiceChallenge],
) -> None:
    """Kill all tracked containers using streaming to prevent memory exhaustion."""
    # Stream containers in batches of 100 to avoid loading all into memory
    for tracker_entry in DockerChallengeTracker.query.yield_per(100):
        challenge = challenges.get(tracker_entry.challenge_id)
        if challenge:
            logging.debug("type:%s", challenge.type)
            logging.debug("instance_id:%s", tracker_entry.instance_id)
            delete_docker(
                docker=docker_config,
                docker_type=challenge.type,
                instance_id=tracker_entry.instance_id,
            )


def _kill_single_container(
    docker_config: DockerConfig,
    container_id: str,
    docker_tracker: list[DockerChallengeTracker],
    challenges: dict[int, DockerChallenge | DockerServiceChallenge],
) -> tuple[dict, int] | None:
    """Kill a specific container by ID."""
    tracker_entry = next((c for c in docker_tracker if c.instance_id == container_id), None)
    if not tracker_entry:
        return {"success": False, "error": "Container not found"}, 404

    challenge = challenges.get(tracker_entry.challenge_id)
    if not challenge:
        return {"success": False, "error": "Challenge not found"}, 404

    delete_docker(
        docker=docker_config, docker_type=challenge.type, instance_id=tracker_entry.instance_id
    )
    return None


def _is_truthy(value: Any) -> bool:
    """Helper to check if a value is truthy (handles bool, string, or other types)."""
    return value is True or str(value).lower() == "true"


@kill_container.route("", methods=["POST"])
class KillContainerAPI(Resource):
    @admins_only
    def post(self):
        # Read from request body (JSON or form data)
        data = request.get_json() or request.form
        if not data:
            return {"success": False, "error": "No data provided"}, 400

        container = data.get("container")
        full = data.get("all")

        docker_config = DockerConfig.query.filter_by(id=1).first_or_404()
        challenges = _get_all_challenges()

        # Kill all containers if requested
        if _is_truthy(full):
            _kill_all_containers(docker_config, challenges)
            return {"success": True}, 200

        # Kill single container
        if container and container != "null":
            # Query only the specific container instead of loading all containers
            tracker_entry = DockerChallengeTracker.query.filter_by(instance_id=container).first()
            if tracker_entry:
                error = _kill_single_container(
                    docker_config, container, [tracker_entry], challenges
                )
                if error:
                    return error
                return {"success": True}, 200

        return {"success": False, "error": "Invalid request"}, 400


def _parse_container_request() -> tuple[str | None, str | None]:
    """
    Parse container creation request data.

    Returns:
        Tuple of (challenge_id, error_message).
        If parsing fails, returns (None, error_message).
    """
    data = request.get_json() or request.form
    if not data:
        return None, "No data provided"

    challenge_id = data.get("id") or data.get("challenge_id")
    if not challenge_id:
        return None, "Challenge ID required"

    return challenge_id, None


def _track_container(
    docker: DockerConfig,
    challenge: DockerChallenge | DockerServiceChallenge,
    session: Any,
    is_teams: bool,
    instance_id: str,
    ports: list[str],
) -> None:
    """Record a new container in the challenge tracker."""
    entry = DockerChallengeTracker(
        team_id=session.id if is_teams else None,
        user_id=session.id if not is_teams else None,
        challenge_id=challenge.id,
        docker_image=challenge.docker_image,
        timestamp=unix_time(datetime.utcnow()),
        revert_time=unix_time(datetime.utcnow()) + CONTAINER_REVERT_TIMEOUT_SECONDS,
        instance_id=instance_id,
        ports=",".join(ports),
        host=str(docker.hostname).split(":")[0],
    )
    db.session.add(entry)
    db.session.commit()


# GET method intentionally removed - container creation must use POST for CSRF protection
@container_namespace.route("", methods=["POST"])
class ContainerAPI(Resource):
    @authed_only
    def post(self):
        """Create a Docker container for a challenge."""
        challenge_id, error = _parse_container_request()
        if error:
            return {"success": False, "error": error}, 400

        docker = DockerConfig.query.filter_by(id=1).first()
        challenge = _get_challenge_by_id(challenge_id)
        if not challenge:
            return {"success": False, "error": "Challenge not found"}, 404

        is_teams = is_teams_mode()
        session = get_current_team() if is_teams else get_current_user()

        result = _handle_container_creation(docker, challenge, session, is_teams)
        if not result:
            error_msg = (
                "Container creation not allowed" if result is None else "Container creation failed"
            )
            return {"success": False, "error": error_msg}, 403 if result is None else 500

        instance_id, ports = result
        _track_container(docker, challenge, session, is_teams, instance_id, ports)

        return {
            "success": True,
            "data": {
                "instance_id": instance_id,
                "ports": ports,
                "host": str(docker.hostname).split(":")[0],
            },
        }, 201


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
        for tracker_entry in tracker:
            data.append(
                {
                    "id": tracker_entry.id,
                    "team_id": tracker_entry.team_id,
                    "user_id": tracker_entry.user_id,
                    "challenge_id": tracker_entry.challenge_id,
                    "docker_image": tracker_entry.docker_image,
                    "timestamp": tracker_entry.timestamp,
                    "revert_time": tracker_entry.revert_time,
                    "instance_id": tracker_entry.instance_id,
                    "ports": tracker_entry.ports.split(","),
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
        return {"success": False, "error": "Failed to load Docker images"}, 500


def _validate_secret_request(data: dict) -> tuple[str | None, str | None, str | None]:
    """
    Validate secret creation request data.

    Args:
        data: Request data containing 'name' and 'data' fields

    Returns:
        Tuple of (secret_name, secret_value, error_message).
        If validation fails, returns (None, None, error_message).
        If validation succeeds, returns (secret_name, secret_value, None).
    """
    if not data:
        return None, None, "No data provided"

    raw_secret_name = data.get("name", "")
    raw_secret_value = data.get("data", "")

    if not isinstance(raw_secret_name, str):
        return None, None, "Secret name must be a string"
    if not isinstance(raw_secret_value, str):
        return None, None, "Secret value must be a string"

    secret_name = raw_secret_name.strip()
    secret_value = raw_secret_value.strip()

    if not secret_name:
        return None, None, "Secret name is required"
    if not secret_value:
        return None, None, "Secret value is required"
    if not re.match(r"^[a-zA-Z0-9._-]+$", secret_name):
        return (
            None,
            None,
            "Secret name must contain only letters, numbers, dots, underscores, and hyphens",
        )

    return secret_name, secret_value, None


def _check_secret_uniqueness(docker: DockerConfig, secret_name: str) -> str | None:
    """
    Check if secret name already exists.

    Args:
        docker: DockerConfig instance
        secret_name: Secret name to check

    Returns:
        Error message if secret exists, None otherwise.
    """
    existing_secrets = get_secrets(docker)
    if any(s["Name"] == secret_name for s in existing_secrets):
        return f"Secret name '{secret_name}' already in use"
    return None


@secret_namespace.route("", methods=["GET", "POST"])
@secret_namespace.route("/<secret_id>", methods=["DELETE"])
class SecretAPI(Resource):
    """
    API for managing Docker secrets.
    GET: Retrieve list of secrets for challenge forms
    POST: Create new secret
    DELETE: Delete secret by ID
    """

    @admins_only
    def get(self):
        docker = DockerConfig.query.filter_by(id=1).first()
        secrets = get_secrets(docker)
        # Return empty list if no secrets available (e.g., Docker not in swarm mode)
        # This is a valid state, not an error
        data = []
        for i in secrets:
            data.append({"name": i["Name"], "id": i["ID"]})
        return {"success": True, "data": data}

    @admins_only
    def post(self):
        """Create a new Docker secret."""
        # Validate request data using helper function
        data = request.get_json() or request.form
        secret_name, secret_value, error = _validate_secret_request(data)
        if error:
            return {"success": False, "error": error}, 400

        # Get Docker config
        docker = DockerConfig.query.filter_by(id=1).first()
        if not docker:
            return {"success": False, "error": "Docker configuration not found"}, 500

        # Validate secure transport (TLS/HTTPS required for secret transmission)
        if not docker.tls_enabled or not request.is_secure:
            return {
                "success": False,
                "error": "Secure transport required. Both HTTPS (browser) and Docker TLS must be enabled to transmit secrets safely.",
            }, 400

        # Check uniqueness using helper function
        uniqueness_error = _check_secret_uniqueness(docker, secret_name)
        if uniqueness_error:
            return {"success": False, "error": uniqueness_error}, 409

        # Create secret
        secret_id, success = create_secret(docker, secret_name, secret_value)
        if not success:
            return {"success": False, "error": "Failed to create secret. Check Docker logs."}, 500

        # Audit logging (log name only, NOT value)
        user = get_current_user()
        username = user.name if user else "Unknown"
        logging.info("Admin '%s' created secret '%s' (ID: %s)", username, secret_name, secret_id)

        return {"success": True, "data": {"id": secret_id, "name": secret_name}}, 201

    @admins_only
    def delete(self, secret_id):
        """Delete a Docker secret by ID."""
        if not secret_id:
            return {"success": False, "error": "Secret ID is required"}, 400

        if not re.match(r"^[a-zA-Z0-9_-]+$", secret_id):
            return {"success": False, "error": "Invalid secret ID format"}, 400

        docker = DockerConfig.query.filter_by(id=1).first()
        if not docker:
            return {"success": False, "error": "Docker configuration not found"}, 500

        # Delete first - Docker API is source of truth (fixes TOCTOU race condition)
        success = delete_secret(docker, secret_id)

        if success:
            # Audit log (ID only - no need to fetch name)
            user = get_current_user()
            username = user.name if user else "Unknown"
            logging.info("Admin '%s' deleted secret ID: %s", username, secret_id)
            return {"success": True, "message": "Secret deleted successfully"}, 200
        else:
            # Query only on failure to determine error type
            current_secrets = get_secrets(docker)
            secret_name = next((s["Name"] for s in current_secrets if s["ID"] == secret_id), None)

            if secret_name:
                return {
                    "success": False,
                    "error": f"Cannot delete secret '{secret_name}' - in use",
                }, 409
            else:
                return {"success": False, "error": "Secret not found"}, 404


@secret_namespace.route("/all", methods=["DELETE"])
class SecretBulkDeleteAPI(Resource):
    """Bulk delete all Docker secrets."""

    @admins_only
    def delete(self):
        docker = DockerConfig.query.filter_by(id=1).first()
        if not docker:
            return {"success": False, "error": "Docker configuration not found"}, 500

        # Get all secrets
        all_secrets = get_secrets(docker)
        if not all_secrets:
            return {
                "success": True,
                "deleted": 0,
                "failed": 0,
                "message": "No secrets to delete",
            }, 200

        # Attempt to delete each secret
        deleted_count = 0
        failed_count = 0
        errors = []

        for secret in all_secrets:
            secret_id = secret["ID"]
            secret_name = secret["Name"]

            success = delete_secret(docker, secret_id)
            if success:
                deleted_count += 1
            else:
                failed_count += 1
                errors.append(f"Failed to delete '{secret_name}' (likely in use)")

        # Audit logging
        user = get_current_user()
        username = user.name if user else "Unknown"
        logging.info(
            "Admin '%s' performed bulk secret deletion: %s deleted, %s failed",
            username,
            deleted_count,
            failed_count,
        )

        all_succeeded = failed_count == 0
        return {
            "success": all_succeeded,
            "deleted": deleted_count,
            "failed": failed_count,
            "errors": errors if errors else [],
        }, 200


@image_ports_namespace.route("", methods=["GET"])
class ImagePortsAPI(Resource):
    """
    This endpoint retrieves the exposed ports from a Docker image's metadata.
    Used to auto-populate the exposed_ports field in challenge creation forms.
    """

    @admins_only
    def get(self):
        image = request.args.get("image")
        if not image:
            return {"success": False, "error": "Image parameter required"}, 400

        if len(image) > 255:
            return {"success": False, "error": "Image name too long"}, 400

        # Validate Docker image name format to prevent SSRF attacks
        # Pattern: [registry/][namespace/]name[:tag][@digest]
        # Examples: nginx, nginx:latest, myregistry.com/user/image:v1.0
        docker_image_pattern = re.compile(
            r"^(?:(?:[a-z0-9]+(?:[._-][a-z0-9]+)*\.)*[a-z0-9]+(?:[._-][a-z0-9]+)*(?::[0-9]+)?/)?"
            r"(?:[a-z0-9._-]+/)?"
            r"[a-z0-9._-]+"
            r"(?::[a-zA-Z0-9._-]+)?"
            r"(?:@sha256:[a-f0-9]{64})?$",
            re.IGNORECASE,
        )

        if not docker_image_pattern.match(image):
            return {
                "success": False,
                "error": "Invalid Docker image name format",
            }, 400

        docker = DockerConfig.query.filter_by(id=1).first()
        if not docker:
            return {"success": False, "error": "Docker config not found"}, 404

        try:
            ports = get_required_ports(docker, image, challenge_ports=None)
            return {"success": True, "ports": ports}
        except Exception as e:
            logging.error("Error in image_ports endpoint: %s: %s", type(e).__name__, e)
            logging.error("Traceback: %s", traceback.format_exc())
            return {"success": False, "error": "Failed to retrieve image port information"}, 500
