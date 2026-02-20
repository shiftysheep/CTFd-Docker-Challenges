"""
Tests for auto-population of exposed_ports from Docker image metadata.

Tests cover:
- resolve_exposed_ports_from_image() helper function
- DockerChallengeType.create() auto-populate logic
- DockerServiceChallengeType.create() auto-populate logic
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import responses


# ============================================================================
# resolve_exposed_ports_from_image tests
# ============================================================================


class TestResolveExposedPortsFromImage:
    """Tests for the resolve_exposed_ports_from_image helper."""

    @pytest.mark.medium
    @responses.activate
    def test_returns_comma_separated_ports_from_image(self, mock_docker_config):
        """Returns comma-separated port string from image ExposedPorts metadata."""
        responses.add(
            responses.GET,
            "http://localhost:2375/images/nginx:latest/json?all=1",
            json={"Config": {"ExposedPorts": {"80/tcp": {}, "443/tcp": {}}}},
            status=200,
        )

        from docker_challenges.functions.general import resolve_exposed_ports_from_image

        result = resolve_exposed_ports_from_image(mock_docker_config, "nginx:latest")

        assert result is not None
        assert set(result.split(",")) == {"80/tcp", "443/tcp"}

    @pytest.mark.medium
    @responses.activate
    def test_returns_none_when_image_has_no_exposed_ports(self, mock_docker_config):
        """Returns None when image metadata has no ExposedPorts."""
        responses.add(
            responses.GET,
            "http://localhost:2375/images/scratch:latest/json?all=1",
            json={"Config": {}},
            status=200,
        )

        from docker_challenges.functions.general import resolve_exposed_ports_from_image

        result = resolve_exposed_ports_from_image(mock_docker_config, "scratch:latest")

        assert result is None

    @pytest.mark.medium
    def test_returns_none_when_docker_unreachable(self, mock_docker_config):
        """Returns None when Docker is unreachable (no crash)."""
        mock_docker_config.hostname = ""

        from docker_challenges.functions.general import resolve_exposed_ports_from_image

        result = resolve_exposed_ports_from_image(mock_docker_config, "nginx:latest")

        assert result is None

    @pytest.mark.medium
    @responses.activate
    def test_returns_none_on_api_error(self, mock_docker_config):
        """Returns None on Docker API error (no crash)."""
        responses.add(
            responses.GET,
            "http://localhost:2375/images/bad:image/json?all=1",
            json={"message": "No such image"},
            status=404,
        )

        from docker_challenges.functions.general import resolve_exposed_ports_from_image

        result = resolve_exposed_ports_from_image(mock_docker_config, "bad:image")

        assert result is None


# ============================================================================
# DockerChallengeType.create() auto-populate tests
# ============================================================================


class TestDockerChallengeTypeCreateAutoPopulate:
    """Tests for auto-populate logic in DockerChallengeType.create()."""

    @pytest.mark.medium
    @patch("docker_challenges.models.container.DockerConfig")
    @patch("docker_challenges.models.container.resolve_exposed_ports_from_image")
    def test_auto_populates_ports_when_exposed_ports_missing(
        self, mock_resolver, mock_docker_config_cls
    ):
        """Auto-populates exposed_ports when not present in request data."""
        from docker_challenges.models.container import DockerChallengeType

        mock_docker_config_cls.query.first.return_value = MagicMock()
        mock_resolver.return_value = "80/tcp,443/tcp"

        mock_request = MagicMock()
        mock_request.form = None
        mock_request.get_json.return_value = {
            "name": "test",
            "docker_image": "nginx:latest",
            "value": 100,
            "category": "web",
            "description": "test challenge",
        }

        with patch("docker_challenges.models.container.DockerChallenge") as mock_cls:
            with patch("docker_challenges.models.container.db"):
                mock_cls.return_value = MagicMock()
                DockerChallengeType.create(mock_request)

        mock_resolver.assert_called_once()

    @pytest.mark.medium
    @patch("docker_challenges.models.container.DockerConfig")
    @patch("docker_challenges.models.container.resolve_exposed_ports_from_image")
    def test_auto_populates_ports_when_exposed_ports_empty_string(
        self, mock_resolver, mock_docker_config_cls
    ):
        """Auto-populates exposed_ports when it is an empty string."""
        from docker_challenges.models.container import DockerChallengeType

        mock_docker_config_cls.query.first.return_value = MagicMock()
        mock_resolver.return_value = "80/tcp"

        mock_request = MagicMock()
        mock_request.form = None
        mock_request.get_json.return_value = {
            "name": "test",
            "docker_image": "nginx:latest",
            "exposed_ports": "",
            "value": 100,
            "category": "web",
            "description": "test challenge",
        }

        with patch("docker_challenges.models.container.DockerChallenge"):
            with patch("docker_challenges.models.container.db"):
                DockerChallengeType.create(mock_request)

        mock_resolver.assert_called_once()

    @pytest.mark.medium
    @patch("docker_challenges.models.container.DockerConfig")
    @patch("docker_challenges.models.container.resolve_exposed_ports_from_image")
    def test_preserves_user_provided_exposed_ports(
        self, mock_resolver, mock_docker_config_cls
    ):
        """Does NOT auto-populate when user explicitly provides exposed_ports."""
        from docker_challenges.models.container import DockerChallengeType

        mock_docker_config_cls.query.first.return_value = MagicMock()

        mock_request = MagicMock()
        mock_request.form = None
        mock_request.get_json.return_value = {
            "name": "test",
            "docker_image": "nginx:latest",
            "exposed_ports": "8080/tcp",
            "value": 100,
            "category": "web",
            "description": "test challenge",
        }

        with patch("docker_challenges.models.container.DockerChallenge"):
            with patch("docker_challenges.models.container.db"):
                DockerChallengeType.create(mock_request)

        mock_resolver.assert_not_called()

    @pytest.mark.medium
    @patch("docker_challenges.models.container.DockerConfig")
    @patch("docker_challenges.models.container.resolve_exposed_ports_from_image")
    def test_graceful_when_docker_config_not_found(
        self, mock_resolver, mock_docker_config_cls
    ):
        """Challenge still created when DockerConfig is not in DB."""
        from docker_challenges.models.container import DockerChallengeType

        mock_docker_config_cls.query.first.return_value = None

        mock_request = MagicMock()
        mock_request.form = None
        mock_request.get_json.return_value = {
            "name": "test",
            "docker_image": "nginx:latest",
            "value": 100,
            "category": "web",
            "description": "test challenge",
        }

        with patch("docker_challenges.models.container.DockerChallenge") as mock_cls:
            with patch("docker_challenges.models.container.db"):
                mock_cls.return_value = MagicMock()
                result = DockerChallengeType.create(mock_request)

        mock_resolver.assert_not_called()
        assert result is not None

    @pytest.mark.medium
    @patch("docker_challenges.models.container.DockerConfig")
    @patch("docker_challenges.models.container.resolve_exposed_ports_from_image")
    def test_graceful_when_resolver_returns_none(
        self, mock_resolver, mock_docker_config_cls
    ):
        """Challenge still created when resolver returns None."""
        from docker_challenges.models.container import DockerChallengeType

        mock_docker_config_cls.query.first.return_value = MagicMock()
        mock_resolver.return_value = None

        mock_request = MagicMock()
        mock_request.form = None
        mock_request.get_json.return_value = {
            "name": "test",
            "docker_image": "nginx:latest",
            "value": 100,
            "category": "web",
            "description": "test challenge",
        }

        with patch("docker_challenges.models.container.DockerChallenge") as mock_cls:
            with patch("docker_challenges.models.container.db"):
                mock_cls.return_value = MagicMock()
                result = DockerChallengeType.create(mock_request)

        assert result is not None


# ============================================================================
# DockerServiceChallengeType.create() auto-populate tests
# ============================================================================


class TestDockerServiceChallengeTypeCreateAutoPopulate:
    """Tests for auto-populate logic in DockerServiceChallengeType.create()."""

    @pytest.mark.medium
    @patch("docker_challenges.models.service.DockerConfig")
    @patch("docker_challenges.models.service.resolve_exposed_ports_from_image")
    def test_auto_populates_ports_when_exposed_ports_missing(
        self, mock_resolver, mock_docker_config_cls
    ):
        """Auto-populates exposed_ports when not present in request data."""
        from docker_challenges.models.service import DockerServiceChallengeType

        mock_docker_config_cls.query.first.return_value = MagicMock()
        mock_resolver.return_value = "80/tcp"

        mock_request = MagicMock()
        mock_request.form = None
        mock_request.get_json.return_value = {
            "name": "test",
            "docker_image": "nginx:latest",
            "docker_secrets_array": "",
            "value": 100,
            "category": "web",
            "description": "test challenge",
        }

        with patch("docker_challenges.models.service.DockerServiceChallenge"):
            with patch("docker_challenges.models.service.db"):
                DockerServiceChallengeType.create(mock_request)

        mock_resolver.assert_called_once()

    @pytest.mark.medium
    @patch("docker_challenges.models.service.DockerConfig")
    @patch("docker_challenges.models.service.resolve_exposed_ports_from_image")
    def test_preserves_user_provided_exposed_ports(
        self, mock_resolver, mock_docker_config_cls
    ):
        """Does NOT auto-populate when user explicitly provides exposed_ports."""
        from docker_challenges.models.service import DockerServiceChallengeType

        mock_docker_config_cls.query.first.return_value = MagicMock()

        mock_request = MagicMock()
        mock_request.form = None
        mock_request.get_json.return_value = {
            "name": "test",
            "docker_image": "nginx:latest",
            "docker_secrets_array": "",
            "exposed_ports": "9090/tcp",
            "value": 100,
            "category": "web",
            "description": "test challenge",
        }

        with patch("docker_challenges.models.service.DockerServiceChallenge"):
            with patch("docker_challenges.models.service.db"):
                DockerServiceChallengeType.create(mock_request)

        mock_resolver.assert_not_called()

    @pytest.mark.medium
    @patch("docker_challenges.models.service.DockerConfig")
    @patch("docker_challenges.models.service.resolve_exposed_ports_from_image")
    def test_graceful_when_docker_config_not_found(
        self, mock_resolver, mock_docker_config_cls
    ):
        """Challenge still created when DockerConfig is not in DB."""
        from docker_challenges.models.service import DockerServiceChallengeType

        mock_docker_config_cls.query.first.return_value = None

        mock_request = MagicMock()
        mock_request.form = None
        mock_request.get_json.return_value = {
            "name": "test",
            "docker_image": "nginx:latest",
            "docker_secrets_array": "",
            "value": 100,
            "category": "web",
            "description": "test challenge",
        }

        with patch("docker_challenges.models.service.DockerServiceChallenge") as mock_cls:
            with patch("docker_challenges.models.service.db"):
                mock_cls.return_value = MagicMock()
                result = DockerServiceChallengeType.create(mock_request)

        mock_resolver.assert_not_called()
        assert result is not None
