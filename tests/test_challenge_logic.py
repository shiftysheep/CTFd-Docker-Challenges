"""Tests verifying that logic: all / logic: any dispatch is handled by BaseChallenge.

The docker plugin must NOT override attempt() or fail() — those overrides bypassed
CTFd 3.8.0's logic dispatch, causing challenges with logic: all to be solved after
just one correct flag submission.

solve() IS overridden to perform container/service cleanup, but it must delegate
Solves record creation to super().solve().
"""
from unittest.mock import MagicMock, call, patch

import pytest

from docker_challenges.models.container import DockerChallengeType
from docker_challenges.models.service import DockerServiceChallengeType


# ---------------------------------------------------------------------------
# attempt() — must NOT be overridden
# ---------------------------------------------------------------------------


def test_container_does_not_override_attempt():
    """DockerChallengeType must inherit attempt() from BaseChallenge."""
    assert "attempt" not in DockerChallengeType.__dict__


def test_service_does_not_override_attempt():
    """DockerServiceChallengeType must inherit attempt() from BaseChallenge."""
    assert "attempt" not in DockerServiceChallengeType.__dict__


# ---------------------------------------------------------------------------
# fail() — must NOT be overridden
# ---------------------------------------------------------------------------


def test_container_does_not_override_fail():
    """DockerChallengeType must inherit fail() from BaseChallenge."""
    assert "fail" not in DockerChallengeType.__dict__


def test_service_does_not_override_fail():
    """DockerServiceChallengeType must inherit fail() from BaseChallenge."""
    assert "fail" not in DockerServiceChallengeType.__dict__


# ---------------------------------------------------------------------------
# solve() — must call cleanup then delegate to super().solve()
# ---------------------------------------------------------------------------


def _make_solve_fixtures():
    user = MagicMock()
    user.id = 1
    team = MagicMock()
    team.id = 2
    challenge = MagicMock()
    challenge.id = 10
    request = MagicMock()
    return user, team, challenge, request


def test_container_solve_calls_cleanup_then_super():
    """DockerChallengeType.solve() cleans up container then delegates to super()."""
    user, team, challenge, request = _make_solve_fixtures()

    with (
        patch(
            "docker_challenges.models.container.DockerConfig"
        ) as mock_config,
        patch(
            "docker_challenges.models.container.cleanup_container_on_solve"
        ) as mock_cleanup,
        patch(
            "docker_challenges.models.container.delete_container"
        ) as mock_delete,
        patch(
            "docker_challenges.models.container.is_teams_mode", return_value=False
        ),
        patch(
            "tests.stubs.ctfd_stubs.BaseChallenge.solve"
        ) as mock_base_solve,
    ):
        mock_config.query.filter_by.return_value.first.return_value = MagicMock()

        DockerChallengeType.solve(user=user, team=team, challenge=challenge, request=request)

        mock_cleanup.assert_called_once()
        # super(DockerChallengeType, cls).solve() dispatches to BaseChallenge.solve
        mock_base_solve.assert_called_once_with(
            user=user, team=team, challenge=challenge, request=request
        )


def test_service_solve_calls_cleanup_then_super():
    """DockerServiceChallengeType.solve() cleans up service then delegates to super()."""
    user, team, challenge, request = _make_solve_fixtures()

    with (
        patch(
            "docker_challenges.models.service.DockerConfig"
        ) as mock_config,
        patch(
            "docker_challenges.models.service.cleanup_container_on_solve"
        ) as mock_cleanup,
        patch(
            "docker_challenges.models.service.delete_service"
        ) as mock_delete,
        patch(
            "docker_challenges.models.service.is_teams_mode", return_value=False
        ),
        patch(
            "tests.stubs.ctfd_stubs.BaseChallenge.solve"
        ) as mock_base_solve,
    ):
        mock_config.query.filter_by.return_value.first.return_value = MagicMock()

        DockerServiceChallengeType.solve(user=user, team=team, challenge=challenge, request=request)

        mock_cleanup.assert_called_once()
        mock_base_solve.assert_called_once_with(
            user=user, team=team, challenge=challenge, request=request
        )


def test_container_solve_records_solve_even_if_cleanup_fails():
    """A container cleanup failure must not prevent the Solves record from being created."""
    user, team, challenge, request = _make_solve_fixtures()

    with (
        patch(
            "docker_challenges.models.container.DockerConfig"
        ) as mock_config,
        patch(
            "docker_challenges.models.container.cleanup_container_on_solve",
            side_effect=RuntimeError("container gone"),
        ),
        patch(
            "docker_challenges.models.container.is_teams_mode", return_value=False
        ),
        patch(
            "tests.stubs.ctfd_stubs.BaseChallenge.solve"
        ) as mock_base_solve,
    ):
        mock_config.query.filter_by.return_value.first.return_value = MagicMock()

        # Must not raise even though cleanup raises
        DockerChallengeType.solve(user=user, team=team, challenge=challenge, request=request)

        mock_base_solve.assert_called_once_with(
            user=user, team=team, challenge=challenge, request=request
        )
