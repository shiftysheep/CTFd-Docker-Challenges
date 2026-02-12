import logging
import os
import tempfile
import traceback
from pathlib import Path

from CTFd.api import CTFd_API_v1
from CTFd.models import Teams, Users, db
from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.challenges import CHALLENGE_CLASSES
from CTFd.utils.config import is_teams_mode
from CTFd.utils.decorators import admins_only
from flask import Blueprint, render_template, request
from sqlalchemy.exc import InternalError

from .api import (
    active_docker_namespace,
    container_namespace,
    docker_namespace,
    image_ports_namespace,
    kill_container,
    secret_namespace,
)

# Re-export API namespaces for external use
__all__ = [
    "active_docker_namespace",
    "container_namespace",
    "docker_namespace",
    "image_ports_namespace",
    "kill_container",
    "secret_namespace",
]
from .functions.general import get_docker_info, get_repositories, get_secrets, is_swarm_mode
from .models.container import DockerChallengeType
from .models.models import DockerChallengeTracker, DockerConfig, DockerConfigForm
from .models.service import DockerServiceChallengeType


def __handle_file_upload(file_key: str, b_obj: DockerConfig, attr_name: str):
    if file_key not in request.files:
        setattr(b_obj, attr_name, "")
        return

    try:
        # Clean up old certificate file if it exists
        old_cert_path = getattr(b_obj, attr_name, None)
        if old_cert_path and Path(old_cert_path).exists():
            try:
                os.unlink(old_cert_path)
                logging.debug("Cleaned up old certificate file: %s", old_cert_path)
            except OSError as e:
                logging.warning("Failed to delete old certificate file %s: %s", old_cert_path, e)

        file_content = request.files[file_key].stream.read()
        if len(file_content) != 0:
            # Use secure temp directory with restrictive permissions and .pem suffix
            with tempfile.NamedTemporaryFile(
                mode="wb",
                suffix=".pem",
                delete=False,
                prefix=f"docker_{attr_name}_",
            ) as tmp_file:
                tmp_file.write(file_content)
                tmp_file.flush()
                # Set restrictive permissions (owner read/write only)
                os.chmod(tmp_file.name, 0o600)
                setattr(b_obj, attr_name, tmp_file.name)
            return
    except Exception as err:
        logging.error(err)
        setattr(b_obj, attr_name, "")


def define_docker_admin(app):
    admin_docker_config = Blueprint(
        "admin_docker_config",
        __name__,
        template_folder="templates",
        static_folder="assets",
    )

    def _validate_tls_certificates(docker: DockerConfig) -> None:
        """Validate that TLS certificate files exist, disable TLS if missing."""
        if not (docker and docker.tls_enabled):
            return

        for key in ["ca_cert", "client_cert", "client_key"]:
            file_name = getattr(docker, key)
            if file_name and not Path(file_name).exists():
                docker.tls_enabled = False
                return

    def _get_or_create_config() -> DockerConfig:
        """Get existing DockerConfig or create a new one."""
        docker = DockerConfig.query.filter_by(id=1).first()
        if not docker:
            logging.info("No docker config was found, setting empty one.")
            docker = DockerConfig()
            db.session.add(docker)
            db.session.commit()
            docker = DockerConfig.query.filter_by(id=1).first()
        return docker

    def _process_docker_config_form(config: DockerConfig) -> None:
        """Process POST form data to update Docker configuration."""
        __handle_file_upload("ca_cert", config, "ca_cert")
        __handle_file_upload("client_cert", config, "client_cert")
        __handle_file_upload("client_key", config, "client_key")

        config.hostname = request.form["hostname"]

        # Handle TLS enablement
        config.tls_enabled = False
        if "tls_enabled" in request.form:
            config.tls_enabled = request.form["tls_enabled"] == "True"

        # Clear TLS certs if TLS is disabled
        if not config.tls_enabled:
            # Clean up certificate files before clearing database references
            for cert_attr in ["ca_cert", "client_cert", "client_key"]:
                cert_path = getattr(config, cert_attr, None)
                if cert_path and Path(cert_path).exists():
                    try:
                        os.unlink(cert_path)
                        logging.debug("Cleaned up %s file: %s", cert_attr, cert_path)
                    except OSError as e:
                        logging.warning("Failed to delete %s file %s: %s", cert_attr, cert_path, e)

            config.ca_cert = None
            config.client_cert = None
            config.client_key = None

        # Process repositories selection
        repositories = request.form.to_dict(flat=False).get("repositories", None)
        if repositories:
            config.repositories = ",".join(repositories)
        else:
            config.repositories = None

        db.session.add(config)
        db.session.commit()

    def _get_repository_choices(docker: DockerConfig, form: DockerConfigForm) -> None:
        """Fetch available Docker repositories and set form choices."""
        try:
            repos = get_repositories(docker)
        except Exception:
            logging.error(traceback.print_exc())
            repos = []

        if len(repos) == 0:
            form.repositories.choices = [("ERROR", "Failed to load repositories")]
        else:
            form.repositories.choices = [(d, d) for d in repos]

    def _get_selected_repositories(config: DockerConfig) -> list:
        """Get currently selected repositories from config."""
        try:
            selected_repos = config.repositories
            if selected_repos is None:
                selected_repos = []
        except Exception:
            logging.error(traceback.print_exc())
            selected_repos = []
        return selected_repos

    @admin_docker_config.route("/admin/docker_config", methods=["GET", "POST"])
    @admins_only
    def docker_config():
        """Admin page for configuring Docker host connection and repositories."""
        # Get or create configuration
        docker = _get_or_create_config()
        form = DockerConfigForm()

        # Validate TLS certificates exist
        _validate_tls_certificates(docker)

        # Process form submission
        if request.method == "POST":
            _process_docker_config_form(docker)
            docker = DockerConfig.query.filter_by(id=1).first()

        # Fetch repositories and populate form choices
        _get_repository_choices(docker, form)

        # Get currently selected repositories
        selected_repos = _get_selected_repositories(docker)

        # Get Docker daemon info
        dinfo = get_docker_info(docker)

        return render_template(
            "docker_config.html",
            config=docker,
            form=form,
            repos=selected_repos,
            info=dinfo,
        )

    app.register_blueprint(admin_docker_config)


def define_docker_status(app):
    admin_docker_status = Blueprint(
        "admin_docker_status",
        __name__,
        template_folder="templates",
        static_folder="assets",
    )

    @admin_docker_status.route("/admin/docker_status", methods=["GET", "POST"])
    @admins_only
    def docker_admin():
        try:
            docker_tracker = DockerChallengeTracker.query.all()
            for i in docker_tracker:
                if is_teams_mode():
                    name = Teams.query.filter_by(id=i.team_id).first()
                    i.team_id = name.name
                else:
                    name = Users.query.filter_by(id=i.user_id).first()
                    i.user_id = name.name
        except InternalError as err:
            logging.error(err)
            return render_template("admin_docker_status.html", dockers=[])

        return render_template("admin_docker_status.html", dockers=docker_tracker)

    app.register_blueprint(admin_docker_status)


def define_docker_secrets(app):
    """Admin blueprint for managing Docker secrets."""
    admin_docker_secrets = Blueprint(
        "admin_docker_secrets",
        __name__,
        template_folder="templates",
        static_folder="assets",
    )

    @admin_docker_secrets.route("/admin/docker_secrets", methods=["GET"])
    @admins_only
    def docker_secrets():
        """Admin page for viewing and managing Docker secrets."""
        try:
            docker = DockerConfig.query.filter_by(id=1).first()
            if not docker:
                logging.error("Docker configuration not found")
                return render_template(
                    "admin_docker_secrets.html",
                    secrets=[],
                    swarm_mode=False,
                    errors=["Docker not configured"],
                    docker=None,
                )

            swarm_mode = is_swarm_mode(docker)
            secrets = get_secrets(docker)
            secrets_sorted = sorted(secrets, key=lambda s: s["Name"])

        except Exception as err:
            logging.error("Error loading secrets: %s", err)
            return render_template(
                "admin_docker_secrets.html",
                secrets=[],
                swarm_mode=False,
                errors=[str(err)],
                docker=None,
            )

        return render_template(
            "admin_docker_secrets.html",
            secrets=secrets_sorted,
            swarm_mode=swarm_mode,
            docker=docker,
        )

    app.register_blueprint(admin_docker_secrets)


def load(app):
    app.db.create_all()

    CHALLENGE_CLASSES["docker"] = DockerChallengeType
    CHALLENGE_CLASSES["docker_service"] = DockerServiceChallengeType

    register_plugin_assets_directory(app, base_path="/plugins/docker_challenges/assets")

    define_docker_admin(app)
    define_docker_status(app)
    define_docker_secrets(app)

    CTFd_API_v1.add_namespace(docker_namespace, "/docker")
    CTFd_API_v1.add_namespace(container_namespace, "/container")
    CTFd_API_v1.add_namespace(active_docker_namespace, "/docker_status")
    CTFd_API_v1.add_namespace(kill_container, "/nuke")
    CTFd_API_v1.add_namespace(secret_namespace, "/secret")
    CTFd_API_v1.add_namespace(image_ports_namespace, "/image_ports")
