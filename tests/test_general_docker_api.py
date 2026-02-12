"""
Tests for Docker API functions in docker_challenges.functions.general.

Uses responses library to mock HTTP calls to Docker API endpoints.
All tests are marked with @pytest.mark.medium as they require HTTP mocking.
"""

from __future__ import annotations

import pytest
import responses
from requests.exceptions import ConnectionError as RequestsConnectionError

from docker_challenges.functions.general import (
    do_request,
    get_docker_info,
    get_repositories,
    get_secrets,
    get_unavailable_ports,
    is_swarm_mode,
)

# ============================================================================
# do_request tests
# ============================================================================


@pytest.mark.medium
def test_do_request_returns_none_when_hostname_empty(mock_docker_config):
    """do_request returns None when hostname is empty or None."""
    mock_docker_config.hostname = ""
    result = do_request(mock_docker_config, "/test")
    assert result is None

    mock_docker_config.hostname = None
    result = do_request(mock_docker_config, "/test")
    assert result is None


@pytest.mark.medium
@responses.activate
def test_do_request_makes_get_request(mock_docker_config):
    """do_request makes GET request and returns Response object."""
    responses.add(
        responses.GET,
        "http://localhost:2375/containers/json",
        json=[{"Id": "abc123"}],
        status=200,
    )

    result = do_request(mock_docker_config, "/containers/json")

    assert result is not None
    assert result.status_code == 200
    assert result.json() == [{"Id": "abc123"}]


@pytest.mark.medium
@responses.activate
def test_do_request_makes_post_request_with_data(mock_docker_config):
    """do_request makes POST request with data payload."""
    responses.add(
        responses.POST,
        "http://localhost:2375/containers/create",
        json={"Id": "new123"},
        status=201,
    )

    data = '{"Image": "nginx:latest"}'
    result = do_request(mock_docker_config, "/containers/create", method="POST", data=data)

    assert result is not None
    assert result.status_code == 201
    assert result.json() == {"Id": "new123"}
    assert len(responses.calls) == 1
    assert responses.calls[0].request.body == data


@pytest.mark.medium
@responses.activate
def test_do_request_makes_delete_request(mock_docker_config):
    """do_request makes DELETE request."""
    responses.add(
        responses.DELETE,
        "http://localhost:2375/containers/abc123",
        status=204,
    )

    result = do_request(mock_docker_config, "/containers/abc123", method="DELETE")

    assert result is not None
    assert result.status_code == 204


@pytest.mark.medium
@responses.activate
def test_do_request_uses_https_when_tls_enabled(mock_docker_config_tls):
    """do_request uses https prefix when tls_enabled is True."""
    responses.add(
        responses.GET,
        "https://localhost:2376/info",
        json={"ID": "test"},
        status=200,
    )

    result = do_request(mock_docker_config_tls, "/info")

    assert result is not None
    assert result.status_code == 200
    # Verify HTTPS was used
    assert responses.calls[0].request.url.startswith("https://")


@pytest.mark.medium
@responses.activate
def test_do_request_returns_none_on_connection_error(mock_docker_config):
    """do_request returns None on ConnectionError."""
    responses.add(
        responses.GET,
        "http://localhost:2375/containers/json",
        body=RequestsConnectionError("Connection refused"),
    )

    result = do_request(mock_docker_config, "/containers/json")

    assert result is None


# ============================================================================
# get_repositories tests
# ============================================================================


@pytest.mark.medium
@responses.activate
def test_get_repositories_returns_deduplicated_repo_names(mock_docker_config):
    """get_repositories returns deduplicated list of repository names without tags."""
    responses.add(
        responses.GET,
        "http://localhost:2375/images/json?all=1",
        json=[
            {"RepoTags": ["nginx:latest"]},
            {"RepoTags": ["redis:7.0"]},
            {"RepoTags": ["nginx:1.25"]},  # Duplicate repo, different tag
            {"RepoTags": ["postgres:15"]},
        ],
        status=200,
    )

    result = get_repositories(mock_docker_config, tags=False)

    assert sorted(result) == ["nginx", "postgres", "redis"]
    assert len(result) == 3  # nginx should appear only once


@pytest.mark.medium
@responses.activate
def test_get_repositories_returns_full_tags_when_tags_true(mock_docker_config):
    """get_repositories returns full image tags when tags=True."""
    responses.add(
        responses.GET,
        "http://localhost:2375/images/json?all=1",
        json=[
            {"RepoTags": ["nginx:latest"]},
            {"RepoTags": ["redis:7.0"]},
            {"RepoTags": ["nginx:1.25"]},
        ],
        status=200,
    )

    result = get_repositories(mock_docker_config, tags=True)

    assert sorted(result) == ["nginx:1.25", "nginx:latest", "redis:7.0"]


@pytest.mark.medium
@responses.activate
def test_get_repositories_filters_by_repos_list(mock_docker_config):
    """get_repositories filters results by repos parameter (list)."""
    responses.add(
        responses.GET,
        "http://localhost:2375/images/json?all=1",
        json=[
            {"RepoTags": ["nginx:latest"]},
            {"RepoTags": ["redis:7.0"]},
            {"RepoTags": ["postgres:15"]},
        ],
        status=200,
    )

    result = get_repositories(mock_docker_config, repos=["nginx", "redis"])

    assert sorted(result) == ["nginx", "redis"]
    assert "postgres" not in result


@pytest.mark.medium
@responses.activate
def test_get_repositories_filters_by_repos_string(mock_docker_config):
    """get_repositories filters results by repos parameter (comma-separated string)."""
    responses.add(
        responses.GET,
        "http://localhost:2375/images/json?all=1",
        json=[
            {"RepoTags": ["nginx:latest"]},
            {"RepoTags": ["redis:7.0"]},
            {"RepoTags": ["postgres:15"]},
        ],
        status=200,
    )

    result = get_repositories(mock_docker_config, repos="nginx,postgres")

    assert sorted(result) == ["nginx", "postgres"]
    assert "redis" not in result


@pytest.mark.medium
@responses.activate
def test_get_repositories_skips_none_and_none_tags(mock_docker_config):
    """get_repositories skips images with RepoTags=null or <none>:<none>."""
    responses.add(
        responses.GET,
        "http://localhost:2375/images/json?all=1",
        json=[
            {"RepoTags": ["nginx:latest"]},
            {"RepoTags": ["<none>:<none>"]},  # Should be filtered out
            {"RepoTags": None},  # Should be filtered out
            {"RepoTags": ["redis:7.0"]},
        ],
        status=200,
    )

    result = get_repositories(mock_docker_config)

    assert sorted(result) == ["nginx", "redis"]
    assert len(result) == 2


@pytest.mark.medium
def test_get_repositories_returns_empty_list_when_docker_unreachable(mock_docker_config):
    """get_repositories returns empty list when Docker API is unreachable."""
    mock_docker_config.hostname = ""  # Will cause do_request to return []

    result = get_repositories(mock_docker_config)

    assert result == []


# ============================================================================
# get_docker_info tests
# ============================================================================


@pytest.mark.medium
@responses.activate
def test_get_docker_info_returns_formatted_version_string(mock_docker_config):
    """get_docker_info returns formatted version string from Docker API."""
    responses.add(
        responses.GET,
        "http://localhost:2375/version",
        json={
            "Components": [
                {"Name": "Engine", "Version": "24.0.7"},
                {"Name": "containerd", "Version": "1.6.25"},
            ]
        },
        status=200,
    )

    result = get_docker_info(mock_docker_config)

    assert "Docker versions:" in result
    assert "Engine: 24.0.7" in result
    assert "containerd: 1.6.25" in result


@pytest.mark.medium
def test_get_docker_info_returns_error_when_docker_unreachable(mock_docker_config):
    """get_docker_info returns error message when Docker API is unreachable."""
    mock_docker_config.hostname = ""  # Will cause do_request to return []

    result = get_docker_info(mock_docker_config)

    assert result == "Failed to get docker version info"


@pytest.mark.medium
@responses.activate
def test_get_docker_info_returns_error_when_components_missing(mock_docker_config):
    """get_docker_info returns error message when Components key is missing."""
    responses.add(
        responses.GET,
        "http://localhost:2375/version",
        json={"Version": "24.0.7"},  # Missing Components key
        status=200,
    )

    result = get_docker_info(mock_docker_config)

    assert result == "Failed to find information required in response."


# ============================================================================
# is_swarm_mode tests
# ============================================================================


@pytest.mark.medium
@responses.activate
def test_is_swarm_mode_returns_true_when_response_is_list(mock_docker_config):
    """is_swarm_mode returns True when /secrets returns a list (swarm active)."""
    responses.add(
        responses.GET,
        "http://localhost:2375/secrets",
        json=[
            {"ID": "sec1", "Spec": {"Name": "my_secret"}},
            {"ID": "sec2", "Spec": {"Name": "db_pass"}},
        ],
        status=200,
    )

    result = is_swarm_mode(mock_docker_config)

    assert result is True


@pytest.mark.medium
@responses.activate
def test_is_swarm_mode_returns_false_when_not_swarm_manager(mock_docker_config):
    """is_swarm_mode returns False when response indicates not a swarm manager."""
    responses.add(
        responses.GET,
        "http://localhost:2375/secrets",
        json={"message": "This node is not a swarm manager."},
        status=503,
    )

    result = is_swarm_mode(mock_docker_config)

    assert result is False


@pytest.mark.medium
def test_is_swarm_mode_returns_false_when_docker_unreachable(mock_docker_config):
    """is_swarm_mode returns False when Docker API is unreachable."""
    mock_docker_config.hostname = ""  # Will cause do_request to return []

    result = is_swarm_mode(mock_docker_config)

    assert result is False


# ============================================================================
# get_secrets tests
# ============================================================================


@pytest.mark.medium
@responses.activate
def test_get_secrets_returns_list_of_id_name_dicts(mock_docker_config):
    """get_secrets returns list of dicts with ID and Name keys."""
    responses.add(
        responses.GET,
        "http://localhost:2375/secrets",
        json=[
            {"ID": "sec1abc", "Spec": {"Name": "my_secret"}},
            {"ID": "sec2def", "Spec": {"Name": "db_pass"}},
        ],
        status=200,
    )

    result = get_secrets(mock_docker_config)

    assert len(result) == 2
    assert result[0] == {"ID": "sec1abc", "Name": "my_secret"}
    assert result[1] == {"ID": "sec2def", "Name": "db_pass"}


@pytest.mark.medium
@responses.activate
def test_get_secrets_returns_empty_list_when_not_swarm_mode(mock_docker_config):
    """get_secrets returns empty list when response has 'message' key (not swarm mode)."""
    responses.add(
        responses.GET,
        "http://localhost:2375/secrets",
        json={"message": "This node is not a swarm manager."},
        status=503,
    )

    result = get_secrets(mock_docker_config)

    assert result == []


# ============================================================================
# get_unavailable_ports tests
# ============================================================================


@pytest.mark.medium
@responses.activate
def test_get_unavailable_ports_returns_combined_container_and_service_ports(mock_docker_config):
    """get_unavailable_ports returns combined list of container and service ports."""
    # Mock container endpoint
    responses.add(
        responses.GET,
        "http://localhost:2375/containers/json?all=1",
        json=[
            {
                "Id": "cont1",
                "Ports": [
                    {"PublicPort": 8080, "PrivatePort": 80},
                    {"PublicPort": 8443, "PrivatePort": 443},
                ],
            },
            {
                "Id": "cont2",
                "Ports": [{"PublicPort": 5432, "PrivatePort": 5432}],
            },
        ],
        status=200,
    )

    # Mock service endpoint (swarm mode)
    responses.add(
        responses.GET,
        "http://localhost:2375/services?all=1",
        json=[
            {
                "ID": "svc1",
                "Endpoint": {
                    "Spec": {
                        "Ports": [
                            {"PublishedPort": 9000, "TargetPort": 80},
                            {"PublishedPort": 9001, "TargetPort": 443},
                        ]
                    }
                },
            }
        ],
        status=200,
    )

    result = get_unavailable_ports(mock_docker_config)

    assert sorted(result) == [5432, 8080, 8443, 9000, 9001]


@pytest.mark.medium
@responses.activate
def test_get_unavailable_ports_returns_only_container_ports_when_not_swarm(mock_docker_config):
    """get_unavailable_ports returns only container ports when services endpoint returns swarm error."""
    # Mock container endpoint
    responses.add(
        responses.GET,
        "http://localhost:2375/containers/json?all=1",
        json=[
            {
                "Id": "cont1",
                "Ports": [{"PublicPort": 8080, "PrivatePort": 80}],
            }
        ],
        status=200,
    )

    # Mock service endpoint with swarm error
    responses.add(
        responses.GET,
        "http://localhost:2375/services?all=1",
        json={"message": "This node is not a swarm manager. Use \"docker swarm init\""},
        status=503,
    )

    result = get_unavailable_ports(mock_docker_config)

    assert result == [8080]


@pytest.mark.medium
def test_get_unavailable_ports_returns_empty_list_when_container_endpoint_unreachable(
    mock_docker_config,
):
    """get_unavailable_ports returns empty list when container endpoint is unreachable."""
    mock_docker_config.hostname = ""  # Will cause do_request to return []

    result = get_unavailable_ports(mock_docker_config)

    assert result == []


# ============================================================================
# do_request None-return safety tests
# ============================================================================


@pytest.mark.medium
def test_get_secrets_returns_empty_on_none_response(mock_docker_config):
    """get_secrets returns empty list when do_request returns None."""
    mock_docker_config.hostname = ""  # Triggers None return from do_request
    result = get_secrets(mock_docker_config)
    assert result == []


@pytest.mark.medium
def test_delete_container_returns_false_on_none_response(mock_docker_config):
    """delete_container returns False when do_request returns None."""
    mock_docker_config.hostname = ""
    from docker_challenges.functions.containers import delete_container
    result = delete_container(mock_docker_config, "nonexistent_id")
    assert result is False


@pytest.mark.medium
def test_delete_service_returns_false_on_none_response(mock_docker_config):
    """delete_service returns False when do_request returns None."""
    mock_docker_config.hostname = ""
    from docker_challenges.functions.services import delete_service
    result = delete_service(mock_docker_config, "nonexistent_id")
    assert result is False
