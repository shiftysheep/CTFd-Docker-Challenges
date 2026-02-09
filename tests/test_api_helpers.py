"""Tests for API helper functions from api/api.py.

These tests validate:
- _is_truthy: Boolean/string truthiness checking
- _validate_secret_request: Secret creation request validation
- _check_secret_uniqueness: Secret name conflict detection

Note: CTFd stubs are injected by conftest.py at module scope before test collection.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from docker_challenges.api.api import (
    _check_secret_uniqueness,
    _is_truthy,
    _validate_secret_request,
)


# ============================================================================
# Tests for _is_truthy
# ============================================================================
class TestIsTruthy:
    """Test suite for _is_truthy helper function."""

    @pytest.mark.light
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            # Boolean True
            (True, True),
            # Boolean False
            (False, False),
            # String variations of "true"
            ("true", True),
            ("True", True),
            ("TRUE", True),
            # String "false"
            ("false", False),
            # None becomes "none" when stringified
            (None, False),
            # Integer 1 is not True (identity check fails, str(1) != "true")
            (1, False),
            # Integer 0
            (0, False),
            # Empty string
            ("", False),
            # Whitespace-only string
            ("  ", False),
            # Other truthy string (not "true")
            ("yes", False),
            # Other string
            ("false ", False),  # Trailing space makes it not match "false"
        ],
    )
    def test_is_truthy_parametrized(self, value, expected):
        """Test _is_truthy with various input types."""
        assert _is_truthy(value) == expected


# ============================================================================
# Tests for _validate_secret_request
# ============================================================================
class TestValidateSecretRequest:
    """Test suite for _validate_secret_request helper function."""

    @pytest.mark.light
    def test_valid_request(self):
        """Valid request with name and data returns (name, value, None)."""
        data = {"name": "my_secret", "data": "secret_value"}
        name, value, error = _validate_secret_request(data)

        assert name == "my_secret"
        assert value == "secret_value"
        assert error is None

    @pytest.mark.light
    def test_none_data(self):
        """None data returns error."""
        name, value, error = _validate_secret_request(None)

        assert name is None
        assert value is None
        assert error == "No data provided"

    @pytest.mark.light
    def test_empty_dict(self):
        """Empty dict is falsy, so returns 'No data provided' error."""
        name, value, error = _validate_secret_request({})

        assert name is None
        assert value is None
        assert error == "No data provided"

    @pytest.mark.light
    def test_missing_name_key(self):
        """Request missing 'name' key returns error."""
        data = {"data": "secret_value"}
        name, value, error = _validate_secret_request(data)

        assert name is None
        assert value is None
        assert error == "Secret name is required"

    @pytest.mark.light
    def test_missing_data_key(self):
        """Request missing 'data' key returns error."""
        data = {"name": "my_secret"}
        name, value, error = _validate_secret_request(data)

        assert name is None
        assert value is None
        assert error == "Secret value is required"

    @pytest.mark.light
    def test_name_with_spaces(self):
        """Secret name with spaces returns validation error."""
        data = {"name": "my secret", "data": "secret_value"}
        name, value, error = _validate_secret_request(data)

        assert name is None
        assert value is None
        assert "must contain only" in error

    @pytest.mark.light
    def test_name_with_special_chars(self):
        """Secret name with special characters returns validation error."""
        data = {"name": "my_secret!", "data": "secret_value"}
        name, value, error = _validate_secret_request(data)

        assert name is None
        assert value is None
        assert "must contain only" in error

    @pytest.mark.light
    def test_valid_name_with_allowed_chars(self):
        """Secret name with dots, underscores, hyphens is valid."""
        data = {"name": "my.secret-name_123", "data": "secret_value"}
        name, value, error = _validate_secret_request(data)

        assert name == "my.secret-name_123"
        assert value == "secret_value"
        assert error is None

    @pytest.mark.light
    def test_whitespace_only_name(self):
        """Whitespace-only name is treated as empty after strip()."""
        data = {"name": "   ", "data": "secret_value"}
        name, value, error = _validate_secret_request(data)

        assert name is None
        assert value is None
        assert error == "Secret name is required"

    @pytest.mark.light
    def test_whitespace_only_value(self):
        """Whitespace-only value is treated as empty after strip()."""
        data = {"name": "my_secret", "data": "   "}
        name, value, error = _validate_secret_request(data)

        assert name is None
        assert value is None
        assert error == "Secret value is required"

    @pytest.mark.light
    def test_name_and_value_with_leading_trailing_spaces(self):
        """Leading/trailing spaces are stripped from name and value."""
        data = {"name": "  my_secret  ", "data": "  secret_value  "}
        name, value, error = _validate_secret_request(data)

        assert name == "my_secret"
        assert value == "secret_value"
        assert error is None


# ============================================================================
# Tests for _check_secret_uniqueness
# ============================================================================
class TestCheckSecretUniqueness:
    """Test suite for _check_secret_uniqueness helper function."""

    @pytest.mark.light
    @patch("docker_challenges.api.api.get_secrets")
    def test_unique_name(self, mock_get_secrets, mock_docker_config):
        """Secret name doesn't exist returns None (no error)."""
        mock_get_secrets.return_value = [
            {"ID": "secret1", "Name": "existing_secret"},
            {"ID": "secret2", "Name": "another_secret"},
        ]

        error = _check_secret_uniqueness(mock_docker_config, "new_secret")

        assert error is None
        mock_get_secrets.assert_called_once_with(mock_docker_config)

    @pytest.mark.light
    @patch("docker_challenges.api.api.get_secrets")
    def test_name_already_exists(self, mock_get_secrets, mock_docker_config):
        """Secret name already exists returns error message with name."""
        mock_get_secrets.return_value = [
            {"ID": "secret1", "Name": "existing_secret"},
            {"ID": "secret2", "Name": "my_secret"},
        ]

        error = _check_secret_uniqueness(mock_docker_config, "my_secret")

        assert error is not None
        assert "my_secret" in error
        assert "already in use" in error
        mock_get_secrets.assert_called_once_with(mock_docker_config)

    @pytest.mark.light
    @patch("docker_challenges.api.api.get_secrets")
    def test_empty_secrets_list(self, mock_get_secrets, mock_docker_config):
        """Empty secrets list returns None (no conflicts possible)."""
        mock_get_secrets.return_value = []

        error = _check_secret_uniqueness(mock_docker_config, "new_secret")

        assert error is None
        mock_get_secrets.assert_called_once_with(mock_docker_config)

    @pytest.mark.light
    @patch("docker_challenges.api.api.get_secrets")
    def test_multiple_secrets_name_matches_one(self, mock_get_secrets, mock_docker_config):
        """Multiple secrets exist, name matches one returns error."""
        mock_get_secrets.return_value = [
            {"ID": "secret1", "Name": "secret_one"},
            {"ID": "secret2", "Name": "duplicate_name"},
            {"ID": "secret3", "Name": "secret_three"},
        ]

        error = _check_secret_uniqueness(mock_docker_config, "duplicate_name")

        assert error is not None
        assert "duplicate_name" in error
        mock_get_secrets.assert_called_once_with(mock_docker_config)

    @pytest.mark.light
    @patch("docker_challenges.api.api.get_secrets")
    def test_case_sensitive_matching(self, mock_get_secrets, mock_docker_config):
        """Secret name matching is case-sensitive."""
        mock_get_secrets.return_value = [{"ID": "secret1", "Name": "MySecret"}]

        # Different case should not match
        error = _check_secret_uniqueness(mock_docker_config, "mysecret")
        assert error is None

        # Exact case should match
        error = _check_secret_uniqueness(mock_docker_config, "MySecret")
        assert error is not None
