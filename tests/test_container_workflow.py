"""Tests for _handle_container_creation() container workflow orchestration.

Tests exercise the complete container creation workflow including stale
cleanup, existing container checks, revert logic, and Docker API failure
handling. All helper functions are patched at the module level.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# _handle_container_creation tests
# ============================================================================


class TestHandleContainerCreation:
    """Tests for the _handle_container_creation workflow function."""

    @pytest.mark.medium
    @patch("docker_challenges.api.api._create_docker_instance")
    @patch("docker_challenges.api.api.get_unavailable_ports")
    @patch("docker_challenges.api.api._should_revert_container")
    @patch("docker_challenges.api.api._get_existing_container")
    @patch("docker_challenges.api.api._cleanup_stale_containers")
    def test_first_time_creation_returns_instance_and_ports(
        self,
        mock_cleanup,
        mock_get_existing,
        mock_should_revert,
        mock_get_ports,
        mock_create,
    ):
        """First-time creation (no existing tracker) returns (instance_id, ports)."""
        from docker_challenges.api.api import _handle_container_creation

        mock_docker = MagicMock()
        mock_challenge = MagicMock()
        mock_challenge.type = "docker"
        mock_challenge.docker_type = "container"
        mock_session = MagicMock()

        mock_get_existing.return_value = None
        mock_get_ports.return_value = [30000, 30001]
        mock_create.return_value = ("container_abc123", ["30002/tcp->80"], '{"HostConfig": {}}')

        result = _handle_container_creation(mock_docker, mock_challenge, mock_session, False)

        assert result is not None
        instance_id, ports = result
        assert instance_id == "container_abc123"
        assert ports == ["30002/tcp->80"]
        mock_cleanup.assert_called_once()
        mock_get_existing.assert_called_once()

    @pytest.mark.medium
    @patch("docker_challenges.api.api._create_docker_instance")
    @patch("docker_challenges.api.api.get_unavailable_ports")
    @patch("docker_challenges.api.api._should_revert_container")
    @patch("docker_challenges.api.api._get_existing_container")
    @patch("docker_challenges.api.api._cleanup_stale_containers")
    def test_existing_container_under_five_minutes_returns_none(
        self,
        mock_cleanup,
        mock_get_existing,
        mock_should_revert,
        mock_get_ports,
        mock_create,
    ):
        """Existing container less than 5 min old returns None (too recent)."""
        from docker_challenges.api.api import _handle_container_creation

        mock_docker = MagicMock()
        mock_challenge = MagicMock()
        mock_session = MagicMock()

        existing = MagicMock()
        mock_get_existing.return_value = existing
        mock_should_revert.return_value = False  # Under 5 minutes

        result = _handle_container_creation(mock_docker, mock_challenge, mock_session, False)

        assert result is None
        mock_create.assert_not_called()

    @pytest.mark.medium
    @patch("docker_challenges.api.api._create_docker_instance")
    @patch("docker_challenges.api.api.get_unavailable_ports")
    @patch("docker_challenges.api.api.delete_docker")
    @patch("docker_challenges.api.api._should_revert_container")
    @patch("docker_challenges.api.api._get_existing_container")
    @patch("docker_challenges.api.api._cleanup_stale_containers")
    def test_existing_container_over_five_minutes_triggers_revert(
        self,
        mock_cleanup,
        mock_get_existing,
        mock_should_revert,
        mock_delete_docker,
        mock_get_ports,
        mock_create,
    ):
        """Existing container over 5 min old triggers delete + recreate (revert flow)."""
        from docker_challenges.api.api import _handle_container_creation

        mock_docker = MagicMock()
        mock_challenge = MagicMock()
        mock_challenge.type = "docker"
        mock_session = MagicMock()

        existing = MagicMock()
        existing.instance_id = "old_container_id"
        mock_get_existing.return_value = existing
        mock_should_revert.return_value = True  # Over 5 minutes
        mock_get_ports.return_value = []
        mock_create.return_value = ("new_container_id", ["30005/tcp->80"], "{}")

        result = _handle_container_creation(mock_docker, mock_challenge, mock_session, False)

        assert result is not None
        instance_id, ports = result
        assert instance_id == "new_container_id"
        mock_delete_docker.assert_called_once_with(
            mock_docker, mock_challenge.type, "old_container_id"
        )

    @pytest.mark.medium
    @patch("docker_challenges.api.api._create_docker_instance")
    @patch("docker_challenges.api.api.get_unavailable_ports")
    @patch("docker_challenges.api.api._should_revert_container")
    @patch("docker_challenges.api.api._get_existing_container")
    @patch("docker_challenges.api.api._cleanup_stale_containers")
    def test_stale_cleanup_runs_before_creation(
        self,
        mock_cleanup,
        mock_get_existing,
        mock_should_revert,
        mock_get_ports,
        mock_create,
    ):
        """Stale container cleanup runs before any creation logic."""
        from docker_challenges.api.api import _handle_container_creation

        mock_docker = MagicMock()
        mock_challenge = MagicMock()
        mock_session = MagicMock()

        mock_get_existing.return_value = None
        mock_get_ports.return_value = []
        mock_create.return_value = ("id", ["port"], "{}")

        _handle_container_creation(mock_docker, mock_challenge, mock_session, True)

        mock_cleanup.assert_called_once_with(mock_docker, mock_session, True)

    @pytest.mark.medium
    @patch("docker_challenges.api.api._create_docker_instance")
    @patch("docker_challenges.api.api.get_unavailable_ports")
    @patch("docker_challenges.api.api._should_revert_container")
    @patch("docker_challenges.api.api._get_existing_container")
    @patch("docker_challenges.api.api._cleanup_stale_containers")
    def test_docker_api_failure_returns_false(
        self,
        mock_cleanup,
        mock_get_existing,
        mock_should_revert,
        mock_get_ports,
        mock_create,
    ):
        """Docker API failure during creation returns False."""
        from docker_challenges.api.api import _handle_container_creation

        mock_docker = MagicMock()
        mock_challenge = MagicMock()
        mock_session = MagicMock()

        mock_get_existing.return_value = None
        mock_get_ports.return_value = []
        mock_create.return_value = (None, None, None)  # Creation failed

        result = _handle_container_creation(mock_docker, mock_challenge, mock_session, False)

        assert result is False

    @pytest.mark.medium
    @patch("docker_challenges.api.api._create_docker_instance")
    @patch("docker_challenges.api.api.get_unavailable_ports")
    @patch("docker_challenges.api.api.delete_docker")
    @patch("docker_challenges.api.api._should_revert_container")
    @patch("docker_challenges.api.api._get_existing_container")
    @patch("docker_challenges.api.api._cleanup_stale_containers")
    def test_revert_continues_on_deletion_failure(
        self,
        mock_cleanup,
        mock_get_existing,
        mock_should_revert,
        mock_delete_docker,
        mock_get_ports,
        mock_create,
    ):
        """Container revert proceeds with creation even if old container deletion fails."""
        from docker_challenges.api.api import _handle_container_creation

        mock_docker = MagicMock()
        mock_challenge = MagicMock()
        mock_challenge.type = "docker"
        mock_session = MagicMock()

        existing = MagicMock()
        existing.instance_id = "old_container_id"
        mock_get_existing.return_value = existing
        mock_should_revert.return_value = True
        mock_delete_docker.return_value = False  # Deletion fails
        mock_get_ports.return_value = []
        mock_create.return_value = ("new_container_id", ["30005/tcp->80"], "{}")

        result = _handle_container_creation(mock_docker, mock_challenge, mock_session, False)

        # Should still proceed with creation despite deletion failure
        assert result is not None
        assert result is not False
        instance_id, ports = result
        assert instance_id == "new_container_id"
        mock_delete_docker.assert_called_once()
        mock_create.assert_called_once()

    @pytest.mark.medium
    @patch("docker_challenges.api.api.db")
    @patch("docker_challenges.api.api.DockerChallengeTracker")
    @patch("docker_challenges.api.api._create_docker_instance")
    @patch("docker_challenges.api.api.get_unavailable_ports")
    @patch("docker_challenges.api.api.delete_docker")
    @patch("docker_challenges.api.api._should_revert_container")
    @patch("docker_challenges.api.api._get_existing_container")
    @patch("docker_challenges.api.api._cleanup_stale_containers")
    def test_stale_tracker_entry_deleted_when_revert_fails(
        self,
        mock_cleanup,
        mock_get_existing,
        mock_should_revert,
        mock_delete_docker,
        mock_get_ports,
        mock_create,
        mock_tracker,
        mock_db,
    ):
        """Stale tracker entry is removed from DB when Docker revert fails."""
        from docker_challenges.api.api import _handle_container_creation

        mock_docker = MagicMock()
        mock_challenge = MagicMock()
        mock_challenge.type = "docker"
        mock_session = MagicMock()

        existing = MagicMock()
        existing.instance_id = "old_container_id"
        mock_get_existing.return_value = existing
        mock_should_revert.return_value = True
        mock_delete_docker.return_value = False  # Revert fails
        mock_get_ports.return_value = []
        mock_create.return_value = ("new_id", ["port"], "{}")

        _handle_container_creation(mock_docker, mock_challenge, mock_session, False)

        mock_tracker.query.filter_by.assert_called_with(instance_id="old_container_id")
        mock_tracker.query.filter_by.return_value.delete.assert_called_once()
        mock_db.session.commit.assert_called_once()

    @pytest.mark.medium
    @patch("docker_challenges.api.api.db")
    @patch("docker_challenges.api.api.DockerChallengeTracker")
    @patch("docker_challenges.api.api._create_docker_instance")
    @patch("docker_challenges.api.api.get_unavailable_ports")
    @patch("docker_challenges.api.api.delete_docker")
    @patch("docker_challenges.api.api._should_revert_container")
    @patch("docker_challenges.api.api._get_existing_container")
    @patch("docker_challenges.api.api._cleanup_stale_containers")
    def test_tracker_not_touched_when_revert_succeeds(
        self,
        mock_cleanup,
        mock_get_existing,
        mock_should_revert,
        mock_delete_docker,
        mock_get_ports,
        mock_create,
        mock_tracker,
        mock_db,
    ):
        """Tracker is not deleted manually when revert succeeds (delete_docker handles it)."""
        from docker_challenges.api.api import _handle_container_creation

        mock_docker = MagicMock()
        mock_challenge = MagicMock()
        mock_challenge.type = "docker"
        mock_session = MagicMock()

        existing = MagicMock()
        existing.instance_id = "old_container_id"
        mock_get_existing.return_value = existing
        mock_should_revert.return_value = True
        mock_delete_docker.return_value = True  # Revert succeeds
        mock_get_ports.return_value = []
        mock_create.return_value = ("new_id", ["port"], "{}")

        _handle_container_creation(mock_docker, mock_challenge, mock_session, False)

        # DockerChallengeTracker should NOT be touched directly (delete_docker already did it)
        mock_tracker.query.filter_by.assert_not_called()
        mock_db.session.commit.assert_not_called()


class TestDeleteDocker:
    """Tests for delete_docker return value behavior."""

    @pytest.mark.medium
    @patch("docker_challenges.api.api.db")
    @patch("docker_challenges.api.api.DockerChallengeTracker")
    @patch("docker_challenges.api.api.delete_container")
    def test_returns_true_on_success(self, mock_delete_container, mock_tracker, mock_db):
        """delete_docker returns True and removes tracker on successful deletion."""
        from docker_challenges.api.api import delete_docker

        mock_docker = MagicMock()
        mock_delete_container.return_value = True

        result = delete_docker(mock_docker, "docker", "container_123")

        assert result is True
        mock_delete_container.assert_called_once_with(mock_docker, "container_123")
        mock_tracker.query.filter_by.assert_called_once_with(instance_id="container_123")
        mock_db.session.commit.assert_called_once()

    @pytest.mark.medium
    @patch("docker_challenges.api.api.db")
    @patch("docker_challenges.api.api.DockerChallengeTracker")
    @patch("docker_challenges.api.api.delete_container")
    def test_returns_false_on_failure(self, mock_delete_container, mock_tracker, mock_db):
        """delete_docker returns False and does NOT remove tracker on failed deletion."""
        from docker_challenges.api.api import delete_docker

        mock_docker = MagicMock()
        mock_delete_container.return_value = False

        result = delete_docker(mock_docker, "docker", "container_123")

        assert result is False
        mock_tracker.query.filter_by.assert_not_called()
        mock_db.session.commit.assert_not_called()


# ============================================================================
# _create_docker_instance tests (container vs service branches)
# ============================================================================


class TestCreateDockerInstance:
    """Tests for _create_docker_instance container vs service branching."""

    @pytest.mark.medium
    @patch("docker_challenges.api.api.create_container")
    def test_container_creation_branch(self, mock_create_container):
        """Container type calls create_container with correct args."""
        from docker_challenges.api.api import _create_docker_instance

        mock_docker = MagicMock()
        mock_challenge = MagicMock()
        mock_challenge.docker_type = "container"
        mock_challenge.docker_image = "nginx:latest"
        mock_challenge.exposed_ports = "80/tcp"
        mock_session = MagicMock()
        mock_session.name = "team1"

        port_bindings = {"30100/tcp": [{"HostPort": "30100"}]}
        mock_create_container.return_value = (
            "cont_id_123",
            json.dumps({"HostConfig": {"PortBindings": port_bindings}}),
        )

        instance_id, ports, data = _create_docker_instance(
            mock_docker, mock_challenge, mock_session, [30000]
        )

        assert instance_id == "cont_id_123"
        assert ports is not None
        assert len(ports) == 1
        mock_create_container.assert_called_once_with(
            mock_docker, "nginx:latest", "team1", [30000], "80/tcp"
        )

    @pytest.mark.medium
    @patch("docker_challenges.api.api.create_service")
    def test_service_creation_branch(self, mock_create_service):
        """Service type calls create_service with correct args."""
        from docker_challenges.api.api import _create_docker_instance

        mock_docker = MagicMock()
        mock_challenge = MagicMock()
        mock_challenge.docker_type = "service"
        mock_challenge.docker_image = "nginx:latest"
        mock_challenge.id = 42
        mock_session = MagicMock()
        mock_session.name = "team1"

        endpoint_spec = {
            "EndpointSpec": {
                "Ports": [
                    {"PublishedPort": 30200, "Protocol": "tcp", "TargetPort": 80},
                ]
            }
        }
        mock_create_service.return_value = ("svc_id_456", json.dumps(endpoint_spec))

        instance_id, ports, data = _create_docker_instance(
            mock_docker, mock_challenge, mock_session, [30000]
        )

        assert instance_id == "svc_id_456"
        assert ports is not None
        assert len(ports) == 1
        assert "30200" in ports[0]
        mock_create_service.assert_called_once_with(
            mock_docker,
            challenge_id=42,
            image="nginx:latest",
            team="team1",
            portbl=[30000],
        )

    @pytest.mark.medium
    @patch("docker_challenges.api.api.create_service")
    def test_service_creation_failure_returns_none(self, mock_create_service):
        """Service creation failure returns (None, None, None)."""
        from docker_challenges.api.api import _create_docker_instance

        mock_docker = MagicMock()
        mock_challenge = MagicMock()
        mock_challenge.docker_type = "service"
        mock_challenge.id = 1
        mock_session = MagicMock()
        mock_session.name = "team1"

        mock_create_service.return_value = (None, None)

        instance_id, ports, data = _create_docker_instance(
            mock_docker, mock_challenge, mock_session, []
        )

        assert instance_id is None
        assert ports is None
        assert data is None

    @pytest.mark.medium
    @patch("docker_challenges.api.api.create_container")
    def test_container_creation_failure_returns_none(self, mock_create_container):
        """Container creation failure returns (None, None, None)."""
        from docker_challenges.api.api import _create_docker_instance

        mock_docker = MagicMock()
        mock_challenge = MagicMock()
        mock_challenge.docker_type = "container"
        mock_challenge.docker_image = "nginx:latest"
        mock_challenge.exposed_ports = "80/tcp"
        mock_session = MagicMock()
        mock_session.name = "team1"

        mock_create_container.return_value = (None, None)

        instance_id, ports, data = _create_docker_instance(
            mock_docker, mock_challenge, mock_session, []
        )

        assert instance_id is None
        assert ports is None
        assert data is None
