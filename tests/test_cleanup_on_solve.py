"""Tests for get_user_container() and cleanup_container_on_solve() in general.py.

Tests verify container lookup logic and the fix that gates tracker deletion on
successful Docker API deletion, preventing orphaned containers.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# get_user_container tests
# ============================================================================


class TestGetUserContainer:
    """Tests for the get_user_container helper."""

    @pytest.mark.medium
    @patch("docker_challenges.models.models.DockerChallengeTracker")
    def test_returns_tracker_in_teams_mode(self, mock_tracker_cls):
        """Returns tracker row filtered by team_id in teams mode."""
        from docker_challenges.functions.general import get_user_container

        mock_user = MagicMock()
        mock_team = MagicMock()
        mock_team.id = 7
        mock_challenge = MagicMock()
        mock_challenge.docker_image = "nginx:latest"
        mock_challenge.id = 1

        expected = MagicMock()
        (
            mock_tracker_cls.query.filter_by.return_value.filter_by.return_value.first.return_value
        ) = expected

        result = get_user_container(mock_user, mock_team, mock_challenge, is_teams=True)

        assert result is expected
        mock_tracker_cls.query.filter_by.assert_called_once_with(
            docker_image="nginx:latest", challenge_id=1
        )

    @pytest.mark.medium
    @patch("docker_challenges.models.models.DockerChallengeTracker")
    def test_returns_tracker_in_user_mode(self, mock_tracker_cls):
        """Returns tracker row filtered by user_id in user mode."""
        from docker_challenges.functions.general import get_user_container

        mock_user = MagicMock()
        mock_user.id = 42
        mock_team = None
        mock_challenge = MagicMock()
        mock_challenge.docker_image = "alpine:latest"
        mock_challenge.id = 2

        expected = MagicMock()
        (
            mock_tracker_cls.query.filter_by.return_value.filter_by.return_value.first.return_value
        ) = expected

        result = get_user_container(mock_user, mock_team, mock_challenge, is_teams=False)

        assert result is expected
        mock_tracker_cls.query.filter_by.assert_called_once_with(
            docker_image="alpine:latest", challenge_id=2
        )

    @pytest.mark.medium
    @patch("docker_challenges.models.models.DockerChallengeTracker")
    def test_returns_none_when_no_match(self, mock_tracker_cls):
        """Returns None when no tracker row exists."""
        from docker_challenges.functions.general import get_user_container

        mock_user = MagicMock()
        mock_team = MagicMock()
        mock_challenge = MagicMock()
        mock_challenge.docker_image = "alpine:latest"
        mock_challenge.id = 3

        (
            mock_tracker_cls.query.filter_by.return_value.filter_by.return_value.first.return_value
        ) = None

        result = get_user_container(mock_user, mock_team, mock_challenge, is_teams=True)

        assert result is None


# ============================================================================
# cleanup_container_on_solve tests
# ============================================================================


class TestCleanupContainerOnSolve:
    """Tests for the cleanup_container_on_solve fix."""

    @pytest.mark.medium
    @patch("docker_challenges.functions.general.get_user_container")
    def test_deletes_tracker_when_delete_func_succeeds(self, mock_get_container):
        """Tracker row is deleted when delete_func returns True."""
        from docker_challenges.functions.general import cleanup_container_on_solve

        mock_docker = MagicMock()
        mock_user = MagicMock()
        mock_team = MagicMock()
        mock_challenge = MagicMock()
        mock_challenge.id = 10

        mock_container = MagicMock()
        mock_container.instance_id = "abc123"
        mock_get_container.return_value = mock_container

        mock_delete_func = MagicMock(return_value=True)

        with patch("docker_challenges.models.models.DockerChallengeTracker") as mock_tracker_cls:
            cleanup_container_on_solve(
                mock_docker,
                mock_user,
                mock_team,
                mock_challenge,
                mock_delete_func,
                is_teams=False,
            )

        mock_delete_func.assert_called_once_with(mock_docker, "abc123")
        mock_tracker_cls.query.filter_by.assert_called_once_with(instance_id="abc123")
        mock_tracker_cls.query.filter_by.return_value.delete.assert_called_once()

    @pytest.mark.medium
    @patch("docker_challenges.functions.general.get_user_container")
    def test_does_not_delete_tracker_when_delete_func_fails(self, mock_get_container):
        """Tracker row is NOT deleted when delete_func returns False."""
        from docker_challenges.functions.general import cleanup_container_on_solve

        mock_docker = MagicMock()
        mock_user = MagicMock()
        mock_team = MagicMock()
        mock_challenge = MagicMock()
        mock_challenge.id = 11

        mock_container = MagicMock()
        mock_container.instance_id = "def456"
        mock_get_container.return_value = mock_container

        mock_delete_func = MagicMock(return_value=False)

        with patch("docker_challenges.models.models.DockerChallengeTracker") as mock_tracker_cls:
            cleanup_container_on_solve(
                mock_docker,
                mock_user,
                mock_team,
                mock_challenge,
                mock_delete_func,
                is_teams=False,
            )

        mock_delete_func.assert_called_once_with(mock_docker, "def456")
        mock_tracker_cls.query.filter_by.assert_not_called()

    @pytest.mark.medium
    @patch("docker_challenges.functions.general.get_user_container")
    def test_logs_warning_when_delete_func_fails(self, mock_get_container):
        """A warning is logged when delete_func returns False."""
        import logging

        from docker_challenges.functions.general import cleanup_container_on_solve

        mock_docker = MagicMock()
        mock_user = MagicMock()
        mock_team = MagicMock()
        mock_challenge = MagicMock()
        mock_challenge.id = 12

        mock_container = MagicMock()
        mock_container.instance_id = "ghi789"
        mock_get_container.return_value = mock_container

        mock_delete_func = MagicMock(return_value=False)

        with patch("docker_challenges.models.models.DockerChallengeTracker"):
            with patch.object(logging, "warning") as mock_warn:
                cleanup_container_on_solve(
                    mock_docker,
                    mock_user,
                    mock_team,
                    mock_challenge,
                    mock_delete_func,
                    is_teams=True,
                )

        mock_warn.assert_called_once()
        args = mock_warn.call_args[0]
        assert "ghi789" in str(args)
        assert "12" in str(args)

    @pytest.mark.medium
    @patch("docker_challenges.functions.general.get_user_container")
    def test_no_op_when_no_container(self, mock_get_container):
        """Does nothing when get_user_container returns None."""
        from docker_challenges.functions.general import cleanup_container_on_solve

        mock_get_container.return_value = None

        mock_delete_func = MagicMock()

        with patch("docker_challenges.models.models.DockerChallengeTracker") as mock_tracker_cls:
            cleanup_container_on_solve(
                MagicMock(),
                MagicMock(),
                MagicMock(),
                MagicMock(),
                mock_delete_func,
                is_teams=False,
            )

        mock_delete_func.assert_not_called()
        mock_tracker_cls.query.filter_by.assert_not_called()
