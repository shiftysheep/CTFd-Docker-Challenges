"""Tests for SecretAPI and SecretBulkDeleteAPI endpoint behavior.

Tests exercise the HTTP-level logic of secret endpoints (validation,
status codes, error handling) WITHOUT Docker or database dependencies.
All external calls are patched at the module level.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from docker_challenges.api.api import SecretAPI, SecretBulkDeleteAPI


# ============================================================================
# SecretAPI GET tests
# ============================================================================


class TestSecretAPIGet:
    """Tests for SecretAPI.get (list secrets)."""

    @pytest.mark.medium
    @patch("docker_challenges.api.api.get_secrets")
    @patch("docker_challenges.api.api.DockerConfig")
    def test_get_returns_secret_list(self, mock_config_cls, mock_get_secrets):
        """GET returns success with list of secrets."""
        mock_docker = MagicMock()
        mock_config_cls.query.filter_by.return_value.first.return_value = mock_docker
        mock_get_secrets.return_value = [
            {"ID": "sec1", "Name": "my_secret"},
            {"ID": "sec2", "Name": "db_pass"},
        ]

        api = SecretAPI()
        result = api.get()

        assert result == {
            "success": True,
            "data": [
                {"name": "my_secret", "id": "sec1"},
                {"name": "db_pass", "id": "sec2"},
            ],
        }

    @pytest.mark.medium
    @patch("docker_challenges.api.api.get_secrets")
    @patch("docker_challenges.api.api.DockerConfig")
    def test_get_returns_empty_list_when_no_secrets(self, mock_config_cls, mock_get_secrets):
        """GET returns success with empty data when no secrets exist."""
        mock_docker = MagicMock()
        mock_config_cls.query.filter_by.return_value.first.return_value = mock_docker
        mock_get_secrets.return_value = []

        api = SecretAPI()
        result = api.get()

        assert result == {"success": True, "data": []}


# ============================================================================
# SecretAPI POST tests
# ============================================================================


class TestSecretAPIPost:
    """Tests for SecretAPI.post (create secret)."""

    @pytest.mark.medium
    @patch("docker_challenges.api.api.get_current_user")
    @patch("docker_challenges.api.api.create_secret")
    @patch("docker_challenges.api.api.get_secrets")
    @patch("docker_challenges.api.api.request")
    @patch("docker_challenges.api.api.DockerConfig")
    def test_post_validates_request_body(
        self, mock_config_cls, mock_request, mock_get_secrets, mock_create, mock_user
    ):
        """POST with missing name returns 400."""
        mock_request.get_json.return_value = {"data": "secret_value"}
        mock_request.form = {}

        api = SecretAPI()
        result, status = api.post()

        assert status == 400
        assert result["success"] is False
        assert "name" in result["error"].lower()

    @pytest.mark.medium
    @patch("docker_challenges.api.api.get_current_user")
    @patch("docker_challenges.api.api.create_secret")
    @patch("docker_challenges.api.api.get_secrets")
    @patch("docker_challenges.api.api.request")
    @patch("docker_challenges.api.api.DockerConfig")
    def test_post_requires_https_and_tls(
        self, mock_config_cls, mock_request, mock_get_secrets, mock_create, mock_user
    ):
        """POST without TLS+HTTPS returns 400."""
        mock_request.get_json.return_value = {"name": "my_secret", "data": "value"}
        mock_request.form = {}
        mock_request.is_secure = False

        mock_docker = MagicMock()
        mock_docker.tls_enabled = False
        mock_config_cls.query.filter_by.return_value.first.return_value = mock_docker

        api = SecretAPI()
        result, status = api.post()

        assert status == 400
        assert result["success"] is False
        assert "secure transport" in result["error"].lower()

    @pytest.mark.medium
    @patch("docker_challenges.api.api.get_current_user")
    @patch("docker_challenges.api.api.create_secret")
    @patch("docker_challenges.api.api.get_secrets")
    @patch("docker_challenges.api.api.request")
    @patch("docker_challenges.api.api.DockerConfig")
    def test_post_creates_secret_successfully(
        self, mock_config_cls, mock_request, mock_get_secrets, mock_create, mock_user
    ):
        """POST with valid data and secure transport returns 201."""
        mock_request.get_json.return_value = {"name": "new_secret", "data": "s3cret"}
        mock_request.form = {}
        mock_request.is_secure = True

        mock_docker = MagicMock()
        mock_docker.tls_enabled = True
        mock_config_cls.query.filter_by.return_value.first.return_value = mock_docker

        mock_get_secrets.return_value = []  # No existing secrets
        mock_create.return_value = ("sec_new_id", True)
        mock_user.return_value = MagicMock(name="admin")

        api = SecretAPI()
        result, status = api.post()

        assert status == 201
        assert result["success"] is True
        assert result["data"]["id"] == "sec_new_id"
        assert result["data"]["name"] == "new_secret"

    @pytest.mark.medium
    @patch("docker_challenges.api.api.get_current_user")
    @patch("docker_challenges.api.api.create_secret")
    @patch("docker_challenges.api.api.get_secrets")
    @patch("docker_challenges.api.api.request")
    @patch("docker_challenges.api.api.DockerConfig")
    def test_post_rejects_duplicate_name(
        self, mock_config_cls, mock_request, mock_get_secrets, mock_create, mock_user
    ):
        """POST with existing secret name returns 409."""
        mock_request.get_json.return_value = {"name": "existing", "data": "value"}
        mock_request.form = {}
        mock_request.is_secure = True

        mock_docker = MagicMock()
        mock_docker.tls_enabled = True
        mock_config_cls.query.filter_by.return_value.first.return_value = mock_docker

        mock_get_secrets.return_value = [{"ID": "sec1", "Name": "existing"}]

        api = SecretAPI()
        result, status = api.post()

        assert status == 409
        assert result["success"] is False
        assert "already in use" in result["error"]


# ============================================================================
# SecretAPI DELETE tests
# ============================================================================


class TestSecretAPIDelete:
    """Tests for SecretAPI.delete (delete single secret)."""

    @pytest.mark.medium
    @patch("docker_challenges.api.api.get_current_user")
    @patch("docker_challenges.api.api.get_secrets")
    @patch("docker_challenges.api.api.delete_secret")
    @patch("docker_challenges.api.api.DockerConfig")
    def test_delete_validates_secret_id_format(
        self, mock_config_cls, mock_delete, mock_get_secrets, mock_user
    ):
        """DELETE with invalid secret_id format returns 400."""
        api = SecretAPI()
        result, status = api.delete("../etc/passwd")

        assert status == 400
        assert result["success"] is False
        assert "invalid" in result["error"].lower()

    @pytest.mark.medium
    @patch("docker_challenges.api.api.get_current_user")
    @patch("docker_challenges.api.api.get_secrets")
    @patch("docker_challenges.api.api.delete_secret")
    @patch("docker_challenges.api.api.DockerConfig")
    def test_delete_succeeds(self, mock_config_cls, mock_delete, mock_get_secrets, mock_user):
        """DELETE with valid ID returns 200 on success."""
        mock_docker = MagicMock()
        mock_config_cls.query.filter_by.return_value.first.return_value = mock_docker
        mock_delete.return_value = True
        mock_user.return_value = MagicMock(name="admin")

        api = SecretAPI()
        result, status = api.delete("abc123")

        assert status == 200
        assert result["success"] is True
        mock_delete.assert_called_once_with(mock_docker, "abc123")

    @pytest.mark.medium
    @patch("docker_challenges.api.api.get_current_user")
    @patch("docker_challenges.api.api.get_secrets")
    @patch("docker_challenges.api.api.delete_secret")
    @patch("docker_challenges.api.api.DockerConfig")
    def test_delete_not_found(self, mock_config_cls, mock_delete, mock_get_secrets, mock_user):
        """DELETE returns 404 when secret does not exist."""
        mock_docker = MagicMock()
        mock_config_cls.query.filter_by.return_value.first.return_value = mock_docker
        mock_delete.return_value = False
        mock_get_secrets.return_value = []  # Secret not found in list either

        api = SecretAPI()
        result, status = api.delete("nonexistent_id")

        assert status == 404
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.medium
    @patch("docker_challenges.api.api.get_current_user")
    @patch("docker_challenges.api.api.get_secrets")
    @patch("docker_challenges.api.api.delete_secret")
    @patch("docker_challenges.api.api.DockerConfig")
    def test_delete_rejects_path_traversal(
        self, mock_config_cls, mock_delete, mock_get_secrets, mock_user
    ):
        """DELETE rejects path traversal attempts in secret_id."""
        api = SecretAPI()

        for bad_id in ["../secret", "sec/../id", "sec;rm -rf", "sec%00id", "sec/id"]:
            result, status = api.delete(bad_id)
            assert status == 400, f"Expected 400 for secret_id={bad_id!r}, got {status}"
            assert result["success"] is False

    @pytest.mark.medium
    @patch("docker_challenges.api.api.get_current_user")
    @patch("docker_challenges.api.api.get_secrets")
    @patch("docker_challenges.api.api.delete_secret")
    @patch("docker_challenges.api.api.DockerConfig")
    def test_delete_rejects_special_chars(
        self, mock_config_cls, mock_delete, mock_get_secrets, mock_user
    ):
        """DELETE rejects special characters in secret_id."""
        api = SecretAPI()

        for bad_id in ["sec!id", "sec@id", "sec#id", "sec$id", "sec id"]:
            result, status = api.delete(bad_id)
            assert status == 400, f"Expected 400 for secret_id={bad_id!r}, got {status}"


# ============================================================================
# SecretBulkDeleteAPI DELETE tests
# ============================================================================


class TestSecretBulkDeleteAPI:
    """Tests for SecretBulkDeleteAPI.delete (bulk delete all secrets)."""

    @pytest.mark.medium
    @patch("docker_challenges.api.api.get_current_user")
    @patch("docker_challenges.api.api.delete_secret")
    @patch("docker_challenges.api.api.get_secrets")
    @patch("docker_challenges.api.api.DockerConfig")
    def test_bulk_delete_all_succeed(
        self, mock_config_cls, mock_get_secrets, mock_delete, mock_user
    ):
        """Bulk delete returns success when all secrets are deleted."""
        mock_docker = MagicMock()
        mock_config_cls.query.filter_by.return_value.first.return_value = mock_docker
        mock_get_secrets.return_value = [
            {"ID": "s1", "Name": "secret_one"},
            {"ID": "s2", "Name": "secret_two"},
        ]
        mock_delete.return_value = True
        mock_user.return_value = MagicMock(name="admin")

        api = SecretBulkDeleteAPI()
        result, status = api.delete()

        assert status == 200
        assert result["success"] is True
        assert result["deleted"] == 2
        assert result["failed"] == 0

    @pytest.mark.medium
    @patch("docker_challenges.api.api.get_current_user")
    @patch("docker_challenges.api.api.delete_secret")
    @patch("docker_challenges.api.api.get_secrets")
    @patch("docker_challenges.api.api.DockerConfig")
    def test_bulk_delete_all_fail(self, mock_config_cls, mock_get_secrets, mock_delete, mock_user):
        """Bulk delete returns success:false when all deletions fail."""
        mock_docker = MagicMock()
        mock_config_cls.query.filter_by.return_value.first.return_value = mock_docker
        mock_get_secrets.return_value = [
            {"ID": "s1", "Name": "in_use_1"},
            {"ID": "s2", "Name": "in_use_2"},
        ]
        mock_delete.return_value = False
        mock_user.return_value = MagicMock(name="admin")

        api = SecretBulkDeleteAPI()
        result, status = api.delete()

        assert status == 200
        assert result["success"] is False
        assert result["deleted"] == 0
        assert result["failed"] == 2
        assert len(result["errors"]) == 2

    @pytest.mark.medium
    @patch("docker_challenges.api.api.get_current_user")
    @patch("docker_challenges.api.api.delete_secret")
    @patch("docker_challenges.api.api.get_secrets")
    @patch("docker_challenges.api.api.DockerConfig")
    def test_bulk_delete_partial_failure(
        self, mock_config_cls, mock_get_secrets, mock_delete, mock_user
    ):
        """Bulk delete with partial failure returns success:false with counts."""
        mock_docker = MagicMock()
        mock_config_cls.query.filter_by.return_value.first.return_value = mock_docker
        mock_get_secrets.return_value = [
            {"ID": "s1", "Name": "deletable"},
            {"ID": "s2", "Name": "in_use"},
            {"ID": "s3", "Name": "also_deletable"},
        ]
        # First and third succeed, second fails
        mock_delete.side_effect = [True, False, True]
        mock_user.return_value = MagicMock(name="admin")

        api = SecretBulkDeleteAPI()
        result, status = api.delete()

        assert status == 200
        assert result["success"] is False  # Partial failure => not success
        assert result["deleted"] == 2
        assert result["failed"] == 1
        assert len(result["errors"]) == 1

    @pytest.mark.medium
    @patch("docker_challenges.api.api.get_current_user")
    @patch("docker_challenges.api.api.delete_secret")
    @patch("docker_challenges.api.api.get_secrets")
    @patch("docker_challenges.api.api.DockerConfig")
    def test_bulk_delete_empty_list(
        self, mock_config_cls, mock_get_secrets, mock_delete, mock_user
    ):
        """Bulk delete with no secrets returns success with zero counts."""
        mock_docker = MagicMock()
        mock_config_cls.query.filter_by.return_value.first.return_value = mock_docker
        mock_get_secrets.return_value = []

        api = SecretBulkDeleteAPI()
        result, status = api.delete()

        assert status == 200
        assert result["success"] is True
        assert result["deleted"] == 0
        assert result["failed"] == 0
        mock_delete.assert_not_called()
