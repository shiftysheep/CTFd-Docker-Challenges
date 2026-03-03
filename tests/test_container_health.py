"""Tests for container health check feature.

Covers:
- get_container_states() state mapping from Docker /containers/json
- get_service_states() state mapping from Docker /tasks
- _CachedDockerState TTL caching behaviour
- DockerStatus.get() endpoint: starting/running/cleanup behaviour
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import responses

from docker_challenges.functions.general import (
    _CachedDockerState,
    _fetch_container_states,
    _fetch_service_states,
    get_container_states,
    get_service_states,
)


# ===========================================================================
# _fetch_container_states unit tests
# ===========================================================================


@pytest.mark.medium
@responses.activate
def test_fetch_container_states_running_no_healthcheck(mock_docker_config):
    """Running container without HEALTHCHECK maps to 'running'."""
    responses.add(
        responses.GET,
        "http://localhost:2375/containers/json?all=1",
        json=[{"Id": "abc123", "State": "running", "Status": "Up 5 minutes"}],
        status=200,
    )
    result = _fetch_container_states(mock_docker_config)
    assert result == {"abc123": "running"}


@pytest.mark.medium
@responses.activate
def test_fetch_container_states_running_healthy(mock_docker_config):
    """Running container with (healthy) status maps to 'running'."""
    responses.add(
        responses.GET,
        "http://localhost:2375/containers/json?all=1",
        json=[{"Id": "abc123", "State": "running", "Status": "Up 5 minutes (healthy)"}],
        status=200,
    )
    result = _fetch_container_states(mock_docker_config)
    assert result == {"abc123": "running"}


@pytest.mark.medium
@responses.activate
def test_fetch_container_states_running_health_starting(mock_docker_config):
    """Running container with (health: starting) status maps to 'starting'."""
    responses.add(
        responses.GET,
        "http://localhost:2375/containers/json?all=1",
        json=[{"Id": "abc123", "State": "running", "Status": "Up 2 seconds (health: starting)"}],
        status=200,
    )
    result = _fetch_container_states(mock_docker_config)
    assert result == {"abc123": "starting"}


@pytest.mark.medium
@responses.activate
def test_fetch_container_states_running_unhealthy(mock_docker_config):
    """Running container with (unhealthy) status maps to 'unhealthy'."""
    responses.add(
        responses.GET,
        "http://localhost:2375/containers/json?all=1",
        json=[{"Id": "abc123", "State": "running", "Status": "Up 10 minutes (unhealthy)"}],
        status=200,
    )
    result = _fetch_container_states(mock_docker_config)
    assert result == {"abc123": "unhealthy"}


@pytest.mark.medium
@responses.activate
def test_fetch_container_states_exited_container(mock_docker_config):
    """Exited container maps to 'stopped'."""
    responses.add(
        responses.GET,
        "http://localhost:2375/containers/json?all=1",
        json=[{"Id": "abc123", "State": "exited", "Status": "Exited (0) 1 hour ago"}],
        status=200,
    )
    result = _fetch_container_states(mock_docker_config)
    assert result == {"abc123": "stopped"}


@pytest.mark.medium
@responses.activate
def test_fetch_container_states_created_container_is_starting(mock_docker_config):
    """Container in 'created' state (just started) maps to 'starting', not 'stopped'."""
    responses.add(
        responses.GET,
        "http://localhost:2375/containers/json?all=1",
        json=[{"Id": "abc123", "State": "created", "Status": "Created"}],
        status=200,
    )
    result = _fetch_container_states(mock_docker_config)
    assert result == {"abc123": "starting"}


@pytest.mark.medium
@responses.activate
def test_fetch_container_states_multiple_containers(mock_docker_config):
    """Multiple containers are all correctly mapped."""
    responses.add(
        responses.GET,
        "http://localhost:2375/containers/json?all=1",
        json=[
            {"Id": "id1", "State": "running", "Status": "Up 1 minute"},
            {"Id": "id2", "State": "running", "Status": "Up 2 seconds (health: starting)"},
            {"Id": "id3", "State": "exited", "Status": "Exited (1) 5 minutes ago"},
        ],
        status=200,
    )
    result = _fetch_container_states(mock_docker_config)
    assert result == {"id1": "running", "id2": "starting", "id3": "stopped"}


@pytest.mark.medium
def test_fetch_container_states_returns_empty_on_failure(mock_docker_config):
    """Returns empty dict when Docker API is unreachable."""
    mock_docker_config.hostname = ""
    result = _fetch_container_states(mock_docker_config)
    assert result == {}


# ===========================================================================
# _fetch_service_states unit tests
# ===========================================================================


@pytest.mark.medium
@responses.activate
def test_fetch_service_states_running_task(mock_docker_config):
    """Service with a running task maps to 'running'."""
    responses.add(
        responses.GET,
        "http://localhost:2375/tasks",
        json=[
            {"ServiceID": "svc1", "Status": {"State": "running"}},
        ],
        status=200,
    )
    result = _fetch_service_states(mock_docker_config)
    assert result == {"svc1": "running"}


@pytest.mark.medium
@responses.activate
def test_fetch_service_states_preparing_task(mock_docker_config):
    """Service with only a preparing task maps to 'starting'."""
    responses.add(
        responses.GET,
        "http://localhost:2375/tasks",
        json=[
            {"ServiceID": "svc1", "Status": {"State": "preparing"}},
        ],
        status=200,
    )
    result = _fetch_service_states(mock_docker_config)
    assert result == {"svc1": "starting"}


@pytest.mark.medium
@responses.activate
def test_fetch_service_states_running_beats_starting(mock_docker_config):
    """Service with both running and preparing tasks reports 'running'."""
    responses.add(
        responses.GET,
        "http://localhost:2375/tasks",
        json=[
            {"ServiceID": "svc1", "Status": {"State": "preparing"}},
            {"ServiceID": "svc1", "Status": {"State": "running"}},
        ],
        status=200,
    )
    result = _fetch_service_states(mock_docker_config)
    assert result == {"svc1": "running"}


@pytest.mark.medium
@responses.activate
def test_fetch_service_states_multiple_services(mock_docker_config):
    """Multiple services are independently mapped."""
    responses.add(
        responses.GET,
        "http://localhost:2375/tasks",
        json=[
            {"ServiceID": "svc1", "Status": {"State": "running"}},
            {"ServiceID": "svc2", "Status": {"State": "starting"}},
        ],
        status=200,
    )
    result = _fetch_service_states(mock_docker_config)
    assert result["svc1"] == "running"
    assert result["svc2"] == "starting"


@pytest.mark.medium
def test_fetch_service_states_returns_empty_on_failure(mock_docker_config):
    """Returns empty dict when Docker API is unreachable."""
    mock_docker_config.hostname = ""
    result = _fetch_service_states(mock_docker_config)
    assert result == {}


@pytest.mark.medium
@responses.activate
def test_fetch_service_states_returns_empty_for_non_swarm(mock_docker_config):
    """Returns empty dict when Docker returns a dict (not swarm manager)."""
    responses.add(
        responses.GET,
        "http://localhost:2375/tasks",
        json={"message": "This node is not a swarm manager."},
        status=503,
    )
    result = _fetch_service_states(mock_docker_config)
    assert result == {}


# ===========================================================================
# _CachedDockerState TTL cache tests
# ===========================================================================


@pytest.mark.medium
def test_cached_docker_state_returns_cached_result_within_ttl(mock_docker_config):
    """_CachedDockerState returns cached state without re-fetching within TTL."""
    # Reset cache state
    _CachedDockerState._container_states = {"id1": "running"}
    _CachedDockerState._container_ts = float("inf")  # Never expires

    with patch(
        "docker_challenges.functions.general._fetch_container_states"
    ) as mock_fetch:
        result = get_container_states(mock_docker_config)

    mock_fetch.assert_not_called()
    assert result == {"id1": "running"}

    # Cleanup
    _CachedDockerState._container_ts = 0.0
    _CachedDockerState._container_states = {}


@pytest.mark.medium
def test_cached_docker_state_fetches_fresh_after_ttl(mock_docker_config):
    """_CachedDockerState re-fetches when cache is expired (ts=0)."""
    _CachedDockerState._container_states = {}
    _CachedDockerState._container_ts = 0.0  # Expired immediately

    fresh_data = {"id2": "starting"}

    with patch(
        "docker_challenges.functions.general._fetch_container_states",
        return_value=fresh_data,
    ) as mock_fetch:
        result = get_container_states(mock_docker_config)

    mock_fetch.assert_called_once_with(mock_docker_config)
    assert result == fresh_data

    # Cleanup
    _CachedDockerState._container_ts = 0.0
    _CachedDockerState._container_states = {}


@pytest.mark.medium
def test_cached_service_state_returns_cached_result_within_ttl(mock_docker_config):
    """_CachedDockerState returns cached service state without re-fetching within TTL."""
    _CachedDockerState._service_states = {"svc1": "running"}
    _CachedDockerState._service_ts = float("inf")

    with patch(
        "docker_challenges.functions.general._fetch_service_states"
    ) as mock_fetch:
        result = get_service_states(mock_docker_config)

    mock_fetch.assert_not_called()
    assert result == {"svc1": "running"}

    # Cleanup
    _CachedDockerState._service_ts = 0.0
    _CachedDockerState._service_states = {}


# ===========================================================================
# DockerStatus.get() endpoint behaviour
# ===========================================================================


class TestDockerStatusHealthGate:
    """Integration-style tests for DockerStatus.get() health check logic."""

    def _make_tracker_entry(
        self, instance_id: str, challenge_id: int = 1, healthy: bool = False
    ) -> MagicMock:
        entry = MagicMock()
        entry.id = 1
        entry.instance_id = instance_id
        entry.challenge_id = challenge_id
        entry.healthy = healthy
        entry.team_id = None
        entry.user_id = "1"
        entry.docker_image = "nginx:latest"
        entry.timestamp = 1000
        entry.revert_time = 1300
        entry.ports = "30001/tcp->80/tcp"
        return entry

    @pytest.mark.medium
    @patch("docker_challenges.api.api.db")
    @patch("docker_challenges.api.api.get_service_states")
    @patch("docker_challenges.api.api.get_container_states")
    @patch("docker_challenges.api.api._is_service_challenge")
    @patch("docker_challenges.api.api.DockerChallengeTracker")
    @patch("docker_challenges.api.api.DockerConfig")
    @patch("docker_challenges.api.api.is_teams_mode")
    @patch("docker_challenges.api.api.get_current_user")
    def test_healthy_entry_returns_running_status(
        self,
        mock_get_user,
        mock_is_teams,
        mock_config,
        mock_tracker,
        mock_is_service,
        mock_container_states,
        mock_service_states,
        mock_db,
    ):
        """Tracker entry with healthy=True returns status='running' with ports and host."""
        from docker_challenges.api.api import DockerStatus

        mock_is_teams.return_value = False
        mock_get_user.return_value = MagicMock(id="1")
        mock_docker = MagicMock()
        mock_docker.hostname = "docker.host:2376"
        mock_config.query.filter_by.return_value.first.return_value = mock_docker

        entry = self._make_tracker_entry("cont_abc", healthy=True)
        mock_tracker.query.filter_by.return_value.__iter__ = MagicMock(return_value=iter([entry]))

        api = DockerStatus()
        result = api.get()

        assert result["success"] is True
        assert len(result["data"]) == 1
        item = result["data"][0]
        assert item["status"] == "running"
        assert "ports" in item
        assert "host" in item

    @pytest.mark.medium
    @patch("docker_challenges.api.api.db")
    @patch("docker_challenges.api.api.get_service_states")
    @patch("docker_challenges.api.api.get_container_states")
    @patch("docker_challenges.api.api._is_service_challenge")
    @patch("docker_challenges.api.api.DockerChallengeTracker")
    @patch("docker_challenges.api.api.DockerConfig")
    @patch("docker_challenges.api.api.is_teams_mode")
    @patch("docker_challenges.api.api.get_current_user")
    def test_unhealthy_entry_starting_returns_starting_without_ports(
        self,
        mock_get_user,
        mock_is_teams,
        mock_config,
        mock_tracker,
        mock_is_service,
        mock_container_states,
        mock_service_states,
        mock_db,
    ):
        """Unhealthy entry with Docker status 'starting' returns status='starting' without ports."""
        from docker_challenges.api.api import DockerStatus

        mock_is_teams.return_value = False
        mock_get_user.return_value = MagicMock(id="1")
        mock_docker = MagicMock()
        mock_docker.hostname = "docker.host:2376"
        mock_config.query.filter_by.return_value.first.return_value = mock_docker

        entry = self._make_tracker_entry("cont_abc", healthy=False)
        mock_tracker.query.filter_by.return_value.__iter__ = MagicMock(return_value=iter([entry]))

        mock_is_service.return_value = False
        mock_container_states.return_value = {"cont_abc": "starting"}
        mock_service_states.return_value = {}

        api = DockerStatus()
        result = api.get()

        assert result["success"] is True
        assert len(result["data"]) == 1
        item = result["data"][0]
        assert item["status"] == "starting"
        assert "ports" not in item
        assert "host" not in item
        # healthy flag should NOT have been updated
        assert entry.healthy is False

    @pytest.mark.medium
    @patch("docker_challenges.api.api.db")
    @patch("docker_challenges.api.api.get_service_states")
    @patch("docker_challenges.api.api.get_container_states")
    @patch("docker_challenges.api.api._is_service_challenge")
    @patch("docker_challenges.api.api.DockerChallengeTracker")
    @patch("docker_challenges.api.api.DockerConfig")
    @patch("docker_challenges.api.api.is_teams_mode")
    @patch("docker_challenges.api.api.get_current_user")
    def test_unhealthy_entry_transitions_to_running(
        self,
        mock_get_user,
        mock_is_teams,
        mock_config,
        mock_tracker,
        mock_is_service,
        mock_container_states,
        mock_service_states,
        mock_db,
    ):
        """Unhealthy entry with Docker status 'running' transitions to healthy=True."""
        from docker_challenges.api.api import DockerStatus

        mock_is_teams.return_value = False
        mock_get_user.return_value = MagicMock(id="1")
        mock_docker = MagicMock()
        mock_docker.hostname = "docker.host:2376"
        mock_config.query.filter_by.return_value.first.return_value = mock_docker

        entry = self._make_tracker_entry("cont_abc", healthy=False)
        mock_tracker.query.filter_by.return_value.__iter__ = MagicMock(return_value=iter([entry]))

        mock_is_service.return_value = False
        mock_container_states.return_value = {"cont_abc": "running"}
        mock_service_states.return_value = {}

        api = DockerStatus()
        result = api.get()

        assert result["success"] is True
        assert len(result["data"]) == 1
        item = result["data"][0]
        assert item["status"] == "running"
        assert "ports" in item
        assert "host" in item
        # healthy flag should have been updated
        assert entry.healthy is True
        mock_db.session.commit.assert_called_once()

    @pytest.mark.medium
    @patch("docker_challenges.api.api.db")
    @patch("docker_challenges.api.api.get_service_states")
    @patch("docker_challenges.api.api.get_container_states")
    @patch("docker_challenges.api.api._is_service_challenge")
    @patch("docker_challenges.api.api.DockerChallengeTracker")
    @patch("docker_challenges.api.api.DockerConfig")
    @patch("docker_challenges.api.api.is_teams_mode")
    @patch("docker_challenges.api.api.get_current_user")
    def test_dead_container_cleans_up_tracker_entry(
        self,
        mock_get_user,
        mock_is_teams,
        mock_config,
        mock_tracker,
        mock_is_service,
        mock_container_states,
        mock_service_states,
        mock_db,
    ):
        """Unhealthy entry not found in Docker states removes tracker entry."""
        from docker_challenges.api.api import DockerStatus

        mock_is_teams.return_value = False
        mock_get_user.return_value = MagicMock(id="1")
        mock_docker = MagicMock()
        mock_docker.hostname = "docker.host:2376"
        mock_config.query.filter_by.return_value.first.return_value = mock_docker

        entry = self._make_tracker_entry("cont_dead", healthy=False)
        mock_tracker.query.filter_by.return_value.__iter__ = MagicMock(return_value=iter([entry]))

        mock_is_service.return_value = False
        mock_container_states.return_value = {"cont_dead": "stopped"}
        mock_service_states.return_value = {}

        api = DockerStatus()
        result = api.get()

        assert result["success"] is True
        # Dead container should NOT appear in response data
        assert len(result["data"]) == 0
        # Tracker entry should be deleted
        mock_tracker.query.filter_by.assert_called_with(id=entry.id)
        mock_tracker.query.filter_by.return_value.delete.assert_called_once()
        mock_db.session.commit.assert_called_once()

    @pytest.mark.medium
    @patch("docker_challenges.api.api.db")
    @patch("docker_challenges.api.api.get_service_states")
    @patch("docker_challenges.api.api.get_container_states")
    @patch("docker_challenges.api.api._is_service_challenge")
    @patch("docker_challenges.api.api.DockerChallengeTracker")
    @patch("docker_challenges.api.api.DockerConfig")
    @patch("docker_challenges.api.api.is_teams_mode")
    @patch("docker_challenges.api.api.get_current_user")
    def test_not_found_in_states_shows_starting(
        self,
        mock_get_user,
        mock_is_teams,
        mock_config,
        mock_tracker,
        mock_is_service,
        mock_container_states,
        mock_service_states,
        mock_db,
    ):
        """Container not in states dict (just created) shows as 'starting', not deleted."""
        from docker_challenges.api.api import DockerStatus

        mock_is_teams.return_value = False
        mock_get_user.return_value = MagicMock(id="1")
        mock_docker = MagicMock()
        mock_docker.hostname = "docker.host:2376"
        mock_config.query.filter_by.return_value.first.return_value = mock_docker

        entry = self._make_tracker_entry("cont_new", healthy=False)
        mock_tracker.query.filter_by.return_value.__iter__ = MagicMock(return_value=iter([entry]))

        mock_is_service.return_value = False
        mock_container_states.return_value = {}  # Not yet visible in Docker
        mock_service_states.return_value = {}

        api = DockerStatus()
        result = api.get()

        assert result["success"] is True
        assert len(result["data"]) == 1
        assert result["data"][0]["status"] == "starting"
        assert "ports" not in result["data"][0]
        # Entry should NOT be deleted
        mock_tracker.query.filter_by.return_value.delete.assert_not_called()

    @pytest.mark.medium
    @patch("docker_challenges.api.api.db")
    @patch("docker_challenges.api.api.get_service_states")
    @patch("docker_challenges.api.api.get_container_states")
    @patch("docker_challenges.api.api._is_service_challenge")
    @patch("docker_challenges.api.api.DockerChallengeTracker")
    @patch("docker_challenges.api.api.DockerConfig")
    @patch("docker_challenges.api.api.is_teams_mode")
    @patch("docker_challenges.api.api.get_current_user")
    def test_stopped_container_cleans_up_tracker_entry(
        self,
        mock_get_user,
        mock_is_teams,
        mock_config,
        mock_tracker,
        mock_is_service,
        mock_container_states,
        mock_service_states,
        mock_db,
    ):
        """Unhealthy entry with Docker status 'stopped' removes tracker entry."""
        from docker_challenges.api.api import DockerStatus

        mock_is_teams.return_value = False
        mock_get_user.return_value = MagicMock(id="1")
        mock_docker = MagicMock()
        mock_docker.hostname = "docker.host:2376"
        mock_config.query.filter_by.return_value.first.return_value = mock_docker

        entry = self._make_tracker_entry("cont_stopped", healthy=False)
        mock_tracker.query.filter_by.return_value.__iter__ = MagicMock(return_value=iter([entry]))

        mock_is_service.return_value = False
        mock_container_states.return_value = {"cont_stopped": "stopped"}
        mock_service_states.return_value = {}

        api = DockerStatus()
        result = api.get()

        assert result["success"] is True
        assert len(result["data"]) == 0
        mock_db.session.commit.assert_called_once()

    @pytest.mark.medium
    @patch("docker_challenges.api.api.db")
    @patch("docker_challenges.api.api.get_service_states")
    @patch("docker_challenges.api.api.get_container_states")
    @patch("docker_challenges.api.api._is_service_challenge")
    @patch("docker_challenges.api.api.DockerChallengeTracker")
    @patch("docker_challenges.api.api.DockerConfig")
    @patch("docker_challenges.api.api.is_teams_mode")
    @patch("docker_challenges.api.api.get_current_user")
    def test_service_challenge_uses_service_states(
        self,
        mock_get_user,
        mock_is_teams,
        mock_config,
        mock_tracker,
        mock_is_service,
        mock_container_states,
        mock_service_states,
        mock_db,
    ):
        """Service challenges look up states in service_states dict, not container_states."""
        from docker_challenges.api.api import DockerStatus

        mock_is_teams.return_value = False
        mock_get_user.return_value = MagicMock(id="1")
        mock_docker = MagicMock()
        mock_docker.hostname = "docker.host:2376"
        mock_config.query.filter_by.return_value.first.return_value = mock_docker

        entry = self._make_tracker_entry("svc_abc", challenge_id=5, healthy=False)
        mock_tracker.query.filter_by.return_value.__iter__ = MagicMock(return_value=iter([entry]))

        mock_is_service.return_value = True  # This is a service challenge
        mock_container_states.return_value = {}  # Not in container states
        mock_service_states.return_value = {"svc_abc": "running"}

        api = DockerStatus()
        result = api.get()

        assert result["success"] is True
        assert len(result["data"]) == 1
        assert result["data"][0]["status"] == "running"
        assert entry.healthy is True
