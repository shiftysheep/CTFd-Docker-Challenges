"""
Tests for create_secret() and delete_secret() in docker_challenges.functions.general.

Uses responses library to mock HTTP calls to Docker API endpoints.
All tests are marked with @pytest.mark.medium as they require HTTP mocking.
"""

from __future__ import annotations

import base64
import json

import pytest
import responses

from docker_challenges.functions.general import create_secret, delete_secret

# ============================================================================
# create_secret tests
# ============================================================================


@pytest.mark.medium
@responses.activate
def test_create_secret_returns_id_on_success(mock_docker_config):
    """create_secret returns (secret_id, True) on 201 response."""
    responses.add(
        responses.POST,
        "http://localhost:2375/secrets/create",
        json={"ID": "newsecret123"},
        status=201,
    )

    secret_id, success = create_secret(mock_docker_config, "my_secret", "s3cret_value")

    assert success is True
    assert secret_id == "newsecret123"


@pytest.mark.medium
@responses.activate
def test_create_secret_sends_base64_encoded_data(mock_docker_config):
    """create_secret base64-encodes the data field in the request payload."""
    responses.add(
        responses.POST,
        "http://localhost:2375/secrets/create",
        json={"ID": "abc123"},
        status=201,
    )

    create_secret(mock_docker_config, "test_secret", "plain_text_value")

    assert len(responses.calls) == 1
    payload = json.loads(responses.calls[0].request.body)
    assert payload["Name"] == "test_secret"
    # Verify the data is base64-encoded
    decoded = base64.b64decode(payload["Data"]).decode("utf-8")
    assert decoded == "plain_text_value"


@pytest.mark.medium
@responses.activate
def test_create_secret_returns_none_on_409_conflict(mock_docker_config):
    """create_secret returns (None, False) on 409 name conflict."""
    responses.add(
        responses.POST,
        "http://localhost:2375/secrets/create",
        json={"message": "rpc error: code = AlreadyExists"},
        status=409,
    )

    secret_id, success = create_secret(mock_docker_config, "existing_secret", "value")

    assert success is False
    assert secret_id is None


@pytest.mark.medium
def test_create_secret_returns_none_on_connection_failure(mock_docker_config):
    """create_secret returns (None, False) when Docker API is unreachable."""
    mock_docker_config.hostname = ""

    secret_id, success = create_secret(mock_docker_config, "my_secret", "value")

    assert success is False
    assert secret_id is None


# ============================================================================
# delete_secret tests
# ============================================================================


@pytest.mark.medium
@responses.activate
def test_delete_secret_returns_true_on_204(mock_docker_config):
    """delete_secret returns True on 204 No Content."""
    responses.add(
        responses.DELETE,
        "http://localhost:2375/secrets/sec123",
        status=204,
    )

    result = delete_secret(mock_docker_config, "sec123")

    assert result is True


@pytest.mark.medium
@responses.activate
def test_delete_secret_returns_false_on_409_in_use(mock_docker_config):
    """delete_secret returns False on 409 (secret in use by service)."""
    responses.add(
        responses.DELETE,
        "http://localhost:2375/secrets/sec456",
        json={"message": "secret 'sec456' is in use by the following services: my_svc"},
        status=409,
    )

    result = delete_secret(mock_docker_config, "sec456")

    assert result is False


@pytest.mark.medium
@responses.activate
def test_delete_secret_returns_false_on_404_not_found(mock_docker_config):
    """delete_secret returns False on 404 (secret not found)."""
    responses.add(
        responses.DELETE,
        "http://localhost:2375/secrets/nonexistent",
        json={"message": "secret nonexistent not found"},
        status=404,
    )

    result = delete_secret(mock_docker_config, "nonexistent")

    assert result is False


@pytest.mark.medium
def test_delete_secret_returns_false_on_connection_failure(mock_docker_config):
    """delete_secret returns False when Docker API is unreachable."""
    mock_docker_config.hostname = ""

    result = delete_secret(mock_docker_config, "sec789")

    assert result is False


# ============================================================================
# Special character/encoding edge cases
# ============================================================================


@pytest.mark.medium
@responses.activate
def test_create_secret_with_unicode_value(mock_docker_config):
    """create_secret handles unicode characters in secret value."""
    responses.add(
        responses.POST,
        "http://localhost:2375/secrets/create",
        json={"ID": "unicode_sec"},
        status=201,
    )

    secret_id, success = create_secret(mock_docker_config, "unicode_secret", "p@ssw\u00f6rd\u2603")

    assert success is True
    assert secret_id == "unicode_sec"
    # Verify base64 round-trip preserves unicode
    payload = json.loads(responses.calls[0].request.body)
    decoded = base64.b64decode(payload["Data"]).decode("utf-8")
    assert decoded == "p@ssw\u00f6rd\u2603"


@pytest.mark.medium
@responses.activate
def test_create_secret_with_newlines_in_value(mock_docker_config):
    """create_secret handles multiline values (e.g., PEM certificates)."""
    pem_value = "-----BEGIN CERTIFICATE-----\nMIIBxTCCAW...\n-----END CERTIFICATE-----"
    responses.add(
        responses.POST,
        "http://localhost:2375/secrets/create",
        json={"ID": "pem_sec"},
        status=201,
    )

    secret_id, success = create_secret(mock_docker_config, "tls_cert", pem_value)

    assert success is True
    payload = json.loads(responses.calls[0].request.body)
    decoded = base64.b64decode(payload["Data"]).decode("utf-8")
    assert decoded == pem_value
    assert "\n" in decoded


@pytest.mark.medium
@responses.activate
def test_create_secret_with_base64_padding_chars(mock_docker_config):
    """create_secret produces correct base64 padding for short values."""
    responses.add(
        responses.POST,
        "http://localhost:2375/secrets/create",
        json={"ID": "pad_sec"},
        status=201,
    )

    secret_id, success = create_secret(mock_docker_config, "short_secret", "a")

    assert success is True
    payload = json.loads(responses.calls[0].request.body)
    assert payload["Data"] == "YQ=="  # base64("a") with padding
