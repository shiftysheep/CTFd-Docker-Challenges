"""Tests for Docker secrets JSON parser and secrets list builder."""

import json
from unittest.mock import MagicMock, patch

import pytest

from docker_challenges.functions.services import _build_secrets_list, _parse_docker_secrets


class TestParseDockerSecrets:
    """Tests for _parse_docker_secrets()."""

    def test_valid_json_returns_list_of_dicts(self):
        raw = '[{"id": "abc123", "protected": true}, {"id": "def456", "protected": false}]'
        result = _parse_docker_secrets(raw)
        assert result == [
            {"id": "abc123", "protected": True},
            {"id": "def456", "protected": False},
        ]

    def test_empty_string_returns_empty_list(self):
        assert _parse_docker_secrets("") == []

    def test_empty_json_array_returns_empty_list(self):
        assert _parse_docker_secrets("[]") == []

    def test_none_returns_empty_list(self):
        assert _parse_docker_secrets(None) == []

    def test_mixed_protected_values(self):
        raw = json.dumps([
            {"id": "s1", "protected": True},
            {"id": "s2", "protected": False},
            {"id": "s3", "protected": True},
        ])
        result = _parse_docker_secrets(raw)
        assert len(result) == 3
        assert result[0]["protected"] is True
        assert result[1]["protected"] is False
        assert result[2]["protected"] is True

    def test_invalid_json_raises_error(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_docker_secrets("not valid json")

    def test_single_secret(self):
        raw = '[{"id": "only_one", "protected": false}]'
        result = _parse_docker_secrets(raw)
        assert len(result) == 1
        assert result[0]["id"] == "only_one"
        assert result[0]["protected"] is False


class TestBuildSecretsList:
    """Tests for _build_secrets_list() with per-secret permissions."""

    def _make_challenge(self, docker_secrets_json):
        """Create a mock challenge with the given docker_secrets JSON string."""
        challenge = MagicMock()
        challenge.docker_secrets = docker_secrets_json
        return challenge

    def _make_docker(self):
        """Create a mock docker config."""
        return MagicMock()

    @patch("docker_challenges.functions.services.get_secrets")
    def test_protected_secret_gets_0o600(self, mock_get_secrets):
        mock_get_secrets.return_value = [
            {"ID": "sec1", "Name": "db_password"},
        ]
        challenge = self._make_challenge('[{"id": "db_password", "protected": true}]')

        result = _build_secrets_list(challenge, self._make_docker())

        assert len(result) == 1
        assert result[0]["File"]["Mode"] == 0o600
        assert result[0]["File"]["Name"] == "/run/secrets/db_password"
        assert result[0]["SecretID"] == "sec1"
        assert result[0]["SecretName"] == "db_password"

    @patch("docker_challenges.functions.services.get_secrets")
    def test_unprotected_secret_gets_0o777(self, mock_get_secrets):
        mock_get_secrets.return_value = [
            {"ID": "sec2", "Name": "api_config"},
        ]
        challenge = self._make_challenge('[{"id": "api_config", "protected": false}]')

        result = _build_secrets_list(challenge, self._make_docker())

        assert len(result) == 1
        assert result[0]["File"]["Mode"] == 0o777

    @patch("docker_challenges.functions.services.get_secrets")
    def test_mixed_permissions(self, mock_get_secrets):
        mock_get_secrets.return_value = [
            {"ID": "sec1", "Name": "db_password"},
            {"ID": "sec2", "Name": "api_config"},
        ]
        challenge = self._make_challenge(
            '[{"id": "db_password", "protected": true}, {"id": "api_config", "protected": false}]'
        )

        result = _build_secrets_list(challenge, self._make_docker())

        assert len(result) == 2
        assert result[0]["File"]["Mode"] == 0o600
        assert result[1]["File"]["Mode"] == 0o777

    @patch("docker_challenges.functions.services.get_secrets")
    def test_empty_secrets_returns_empty_list(self, mock_get_secrets):
        mock_get_secrets.return_value = [
            {"ID": "sec1", "Name": "db_password"},
        ]
        challenge = self._make_challenge("[]")

        result = _build_secrets_list(challenge, self._make_docker())

        assert result == []

    @patch("docker_challenges.functions.services.get_secrets")
    def test_secret_id_not_found_in_docker_is_skipped(self, mock_get_secrets):
        mock_get_secrets.return_value = [
            {"ID": "sec1", "Name": "db_password"},
        ]
        challenge = self._make_challenge('[{"id": "nonexistent", "protected": true}]')

        result = _build_secrets_list(challenge, self._make_docker())

        assert result == []

    @patch("docker_challenges.functions.services.get_secrets")
    def test_missing_protected_defaults_to_false(self, mock_get_secrets):
        mock_get_secrets.return_value = [
            {"ID": "sec1", "Name": "db_password"},
        ]
        challenge = self._make_challenge('[{"id": "db_password"}]')

        result = _build_secrets_list(challenge, self._make_docker())

        assert len(result) == 1
        assert result[0]["File"]["Mode"] == 0o777

    @patch("docker_challenges.functions.services.get_secrets")
    def test_file_uid_gid_are_set(self, mock_get_secrets):
        mock_get_secrets.return_value = [
            {"ID": "sec1", "Name": "test_secret"},
        ]
        challenge = self._make_challenge('[{"id": "test_secret", "protected": false}]')

        result = _build_secrets_list(challenge, self._make_docker())

        assert result[0]["File"]["UID"] == "1"
        assert result[0]["File"]["GID"] == "1"

    @patch("docker_challenges.functions.services.get_secrets")
    def test_legacy_swarm_id_matches_by_fallback(self, mock_get_secrets):
        """Old DB entries storing Swarm IDs still match via ID fallback, with a warning logged."""
        mock_get_secrets.return_value = [
            {"ID": "abc123swarmid", "Name": "db_password"},
        ]
        # Stored value is the Swarm ID (legacy format)
        challenge = self._make_challenge('[{"id": "abc123swarmid", "protected": false}]')

        with patch("docker_challenges.functions.services.logging") as mock_log:
            result = _build_secrets_list(challenge, self._make_docker())

        assert len(result) == 1
        assert result[0]["SecretID"] == "abc123swarmid"
        assert result[0]["SecretName"] == "db_password"
        mock_log.warning.assert_called_once()
        warning_msg = mock_log.warning.call_args[0][0]
        assert "legacy" in warning_msg.lower() or "swarm id" in warning_msg.lower()

    @patch("docker_challenges.functions.services.get_secrets")
    def test_missing_secret_logs_warning(self, mock_get_secrets):
        """A configured secret that doesn't exist in Docker is skipped with a warning."""
        mock_get_secrets.return_value = [
            {"ID": "sec1", "Name": "existing_secret"},
        ]
        challenge = self._make_challenge('[{"id": "ghost_secret", "protected": true}]')

        with patch("docker_challenges.functions.services.logging") as mock_log:
            result = _build_secrets_list(challenge, self._make_docker())

        assert result == []
        mock_log.warning.assert_called_once()
        warning_msg = mock_log.warning.call_args[0][0]
        assert "not found" in warning_msg.lower() or "skipping" in warning_msg.lower()
