"""Tests for challenge deletion Docker resource cleanup.

Verifies that both DockerServiceChallengeType.delete() and DockerChallengeType.delete()
properly stop running Docker resources and remove tracker entries before cleaning up
CTFd DB records.
"""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest


# ============================================================================
# DockerServiceChallengeType.delete() tests
# ============================================================================


class TestDockerServiceChallengeTypeDelete:
    """Tests for DockerServiceChallengeType.delete() Docker cleanup."""

    @pytest.mark.medium
    @patch("docker_challenges.models.service.Challenges")
    @patch("docker_challenges.models.service.DockerServiceChallenge")
    @patch("docker_challenges.models.service.Hints")
    @patch("docker_challenges.models.service.Tags")
    @patch("docker_challenges.models.service.ChallengeFiles")
    @patch("docker_challenges.models.service.delete_file")
    @patch("docker_challenges.models.service.Flags")
    @patch("docker_challenges.models.service.Solves")
    @patch("docker_challenges.models.service.Fails")
    @patch("docker_challenges.models.service.db")
    @patch("docker_challenges.models.service.DockerChallengeTracker")
    @patch("docker_challenges.models.service.delete_service")
    @patch("docker_challenges.models.service.DockerConfig")
    def test_delete_calls_delete_service_for_each_tracker_entry(
        self, mock_docker_config, mock_delete_service, mock_tracker, mock_db,
        mock_fails, mock_solves, mock_flags, mock_delete_file, mock_files,
        mock_tags, mock_hints, mock_docker_service, mock_challenges
    ):
        """delete() calls delete_service once per tracker entry for the challenge."""
        from docker_challenges.models.service import DockerServiceChallengeType

        mock_challenge = MagicMock()
        mock_challenge.id = 42

        mock_docker = MagicMock()
        mock_docker_config.query.filter_by.return_value.first.return_value = mock_docker

        entry1 = MagicMock()
        entry1.instance_id = "svc_aaa"
        entry2 = MagicMock()
        entry2.instance_id = "svc_bbb"
        mock_tracker.query.filter_by.return_value.all.return_value = [entry1, entry2]
        mock_delete_service.return_value = True

        # Mock all the CTFd database queries
        mock_fails.query.filter_by.return_value.delete.return_value = None
        mock_solves.query.filter_by.return_value.delete.return_value = None
        mock_flags.query.filter_by.return_value.delete.return_value = None
        mock_files.query.filter_by.return_value.all.return_value = []
        mock_tags.query.filter_by.return_value.delete.return_value = None
        mock_hints.query.filter_by.return_value.delete.return_value = None
        mock_docker_service.query.filter_by.return_value.delete.return_value = None
        mock_challenges.query.filter_by.return_value.delete.return_value = None

        DockerServiceChallengeType.delete(mock_challenge)

        assert mock_delete_service.call_count == 2
        mock_delete_service.assert_any_call(mock_docker, "svc_aaa")
        mock_delete_service.assert_any_call(mock_docker, "svc_bbb")

    @pytest.mark.medium
    @patch("docker_challenges.models.service.Challenges")
    @patch("docker_challenges.models.service.DockerServiceChallenge")
    @patch("docker_challenges.models.service.Hints")
    @patch("docker_challenges.models.service.Tags")
    @patch("docker_challenges.models.service.ChallengeFiles")
    @patch("docker_challenges.models.service.delete_file")
    @patch("docker_challenges.models.service.Flags")
    @patch("docker_challenges.models.service.Solves")
    @patch("docker_challenges.models.service.Fails")
    @patch("docker_challenges.models.service.db")
    @patch("docker_challenges.models.service.DockerChallengeTracker")
    @patch("docker_challenges.models.service.delete_service")
    @patch("docker_challenges.models.service.DockerConfig")
    def test_delete_removes_tracker_entries_even_when_service_deletion_fails(
        self, mock_docker_config, mock_delete_service, mock_tracker, mock_db,
        mock_fails, mock_solves, mock_flags, mock_delete_file, mock_files,
        mock_tags, mock_hints, mock_docker_service, mock_challenges
    ):
        """Tracker entries are deleted even when delete_service returns False."""
        from docker_challenges.models.service import DockerServiceChallengeType

        mock_challenge = MagicMock()
        mock_challenge.id = 42

        mock_docker = MagicMock()
        mock_docker_config.query.filter_by.return_value.first.return_value = mock_docker

        entry = MagicMock()
        entry.instance_id = "svc_fail"
        mock_tracker.query.filter_by.return_value.all.return_value = [entry]
        mock_delete_service.return_value = False  # Docker deletion fails

        # Mock all the CTFd database queries
        mock_fails.query.filter_by.return_value.delete.return_value = None
        mock_solves.query.filter_by.return_value.delete.return_value = None
        mock_flags.query.filter_by.return_value.delete.return_value = None
        mock_files.query.filter_by.return_value.all.return_value = []
        mock_tags.query.filter_by.return_value.delete.return_value = None
        mock_hints.query.filter_by.return_value.delete.return_value = None
        mock_docker_service.query.filter_by.return_value.delete.return_value = None
        mock_challenges.query.filter_by.return_value.delete.return_value = None

        DockerServiceChallengeType.delete(mock_challenge)

        # Tracker bulk delete must still be called
        mock_tracker.query.filter_by.assert_any_call(challenge_id=42)

    @pytest.mark.medium
    @patch("docker_challenges.models.service.Challenges")
    @patch("docker_challenges.models.service.DockerServiceChallenge")
    @patch("docker_challenges.models.service.Hints")
    @patch("docker_challenges.models.service.Tags")
    @patch("docker_challenges.models.service.ChallengeFiles")
    @patch("docker_challenges.models.service.delete_file")
    @patch("docker_challenges.models.service.Flags")
    @patch("docker_challenges.models.service.Solves")
    @patch("docker_challenges.models.service.Fails")
    @patch("docker_challenges.models.service.db")
    @patch("docker_challenges.models.service.DockerChallengeTracker")
    @patch("docker_challenges.models.service.delete_service")
    @patch("docker_challenges.models.service.DockerConfig")
    def test_delete_skips_docker_when_no_config(
        self, mock_docker_config, mock_delete_service, mock_tracker, mock_db,
        mock_fails, mock_solves, mock_flags, mock_delete_file, mock_files,
        mock_tags, mock_hints, mock_docker_service, mock_challenges
    ):
        """delete() skips Docker calls gracefully when DockerConfig is not found."""
        from docker_challenges.models.service import DockerServiceChallengeType

        mock_challenge = MagicMock()
        mock_challenge.id = 99

        mock_docker_config.query.filter_by.return_value.first.return_value = None  # No config

        entry = MagicMock()
        entry.instance_id = "svc_orphan"
        mock_tracker.query.filter_by.return_value.all.return_value = [entry]

        # Mock all the CTFd database queries
        mock_fails.query.filter_by.return_value.delete.return_value = None
        mock_solves.query.filter_by.return_value.delete.return_value = None
        mock_flags.query.filter_by.return_value.delete.return_value = None
        mock_files.query.filter_by.return_value.all.return_value = []
        mock_tags.query.filter_by.return_value.delete.return_value = None
        mock_hints.query.filter_by.return_value.delete.return_value = None
        mock_docker_service.query.filter_by.return_value.delete.return_value = None
        mock_challenges.query.filter_by.return_value.delete.return_value = None

        DockerServiceChallengeType.delete(mock_challenge)

        mock_delete_service.assert_not_called()
        # Tracker delete should still be called
        mock_tracker.query.filter_by.assert_any_call(challenge_id=99)

    @pytest.mark.medium
    @patch("docker_challenges.models.service.Challenges")
    @patch("docker_challenges.models.service.DockerServiceChallenge")
    @patch("docker_challenges.models.service.Hints")
    @patch("docker_challenges.models.service.Tags")
    @patch("docker_challenges.models.service.ChallengeFiles")
    @patch("docker_challenges.models.service.delete_file")
    @patch("docker_challenges.models.service.Flags")
    @patch("docker_challenges.models.service.Solves")
    @patch("docker_challenges.models.service.Fails")
    @patch("docker_challenges.models.service.db")
    @patch("docker_challenges.models.service.DockerChallengeTracker")
    @patch("docker_challenges.models.service.delete_service")
    @patch("docker_challenges.models.service.DockerConfig")
    def test_delete_commits_once(
        self, mock_docker_config, mock_delete_service, mock_tracker, mock_db,
        mock_fails, mock_solves, mock_flags, mock_delete_file, mock_files,
        mock_tags, mock_hints, mock_docker_service, mock_challenges
    ):
        """delete() calls db.session.commit() exactly once."""
        from docker_challenges.models.service import DockerServiceChallengeType

        mock_challenge = MagicMock()
        mock_challenge.id = 10

        mock_docker = MagicMock()
        mock_docker_config.query.filter_by.return_value.first.return_value = mock_docker
        mock_tracker.query.filter_by.return_value.all.return_value = []
        mock_delete_service.return_value = True

        # Mock all the CTFd database queries
        mock_fails.query.filter_by.return_value.delete.return_value = None
        mock_solves.query.filter_by.return_value.delete.return_value = None
        mock_flags.query.filter_by.return_value.delete.return_value = None
        mock_files.query.filter_by.return_value.all.return_value = []
        mock_tags.query.filter_by.return_value.delete.return_value = None
        mock_hints.query.filter_by.return_value.delete.return_value = None
        mock_docker_service.query.filter_by.return_value.delete.return_value = None
        mock_challenges.query.filter_by.return_value.delete.return_value = None

        DockerServiceChallengeType.delete(mock_challenge)

        mock_db.session.commit.assert_called_once()


# ============================================================================
# DockerChallengeType.delete() tests
# ============================================================================


class TestDockerChallengeTypeDelete:
    """Tests for DockerChallengeType.delete() Docker cleanup."""

    @pytest.mark.medium
    @patch("docker_challenges.models.container.Challenges")
    @patch("docker_challenges.models.container.DockerChallenge")
    @patch("docker_challenges.models.container.Hints")
    @patch("docker_challenges.models.container.Tags")
    @patch("docker_challenges.models.container.ChallengeFiles")
    @patch("docker_challenges.models.container.delete_file")
    @patch("docker_challenges.models.container.Flags")
    @patch("docker_challenges.models.container.Solves")
    @patch("docker_challenges.models.container.Fails")
    @patch("docker_challenges.models.container.db")
    @patch("docker_challenges.models.container.DockerChallengeTracker")
    @patch("docker_challenges.models.container.delete_container")
    @patch("docker_challenges.models.container.DockerConfig")
    def test_delete_calls_delete_container_for_each_tracker_entry(
        self, mock_docker_config, mock_delete_container, mock_tracker, mock_db,
        mock_fails, mock_solves, mock_flags, mock_delete_file, mock_files,
        mock_tags, mock_hints, mock_docker_challenge, mock_challenges
    ):
        """delete() calls delete_container once per tracker entry for the challenge."""
        from docker_challenges.models.container import DockerChallengeType

        mock_challenge = MagicMock()
        mock_challenge.id = 55

        mock_docker = MagicMock()
        mock_docker_config.query.filter_by.return_value.first.return_value = mock_docker

        entry1 = MagicMock()
        entry1.instance_id = "cont_111"
        entry2 = MagicMock()
        entry2.instance_id = "cont_222"
        mock_tracker.query.filter_by.return_value.all.return_value = [entry1, entry2]
        mock_delete_container.return_value = True

        # Mock all the CTFd database queries
        mock_fails.query.filter_by.return_value.delete.return_value = None
        mock_solves.query.filter_by.return_value.delete.return_value = None
        mock_flags.query.filter_by.return_value.delete.return_value = None
        mock_files.query.filter_by.return_value.all.return_value = []
        mock_tags.query.filter_by.return_value.delete.return_value = None
        mock_hints.query.filter_by.return_value.delete.return_value = None
        mock_docker_challenge.query.filter_by.return_value.delete.return_value = None
        mock_challenges.query.filter_by.return_value.delete.return_value = None

        DockerChallengeType.delete(mock_challenge)

        assert mock_delete_container.call_count == 2
        mock_delete_container.assert_any_call(mock_docker, "cont_111")
        mock_delete_container.assert_any_call(mock_docker, "cont_222")

    @pytest.mark.medium
    @patch("docker_challenges.models.container.Challenges")
    @patch("docker_challenges.models.container.DockerChallenge")
    @patch("docker_challenges.models.container.Hints")
    @patch("docker_challenges.models.container.Tags")
    @patch("docker_challenges.models.container.ChallengeFiles")
    @patch("docker_challenges.models.container.delete_file")
    @patch("docker_challenges.models.container.Flags")
    @patch("docker_challenges.models.container.Solves")
    @patch("docker_challenges.models.container.Fails")
    @patch("docker_challenges.models.container.db")
    @patch("docker_challenges.models.container.DockerChallengeTracker")
    @patch("docker_challenges.models.container.delete_container")
    @patch("docker_challenges.models.container.DockerConfig")
    def test_delete_removes_tracker_entries_even_when_container_deletion_fails(
        self, mock_docker_config, mock_delete_container, mock_tracker, mock_db,
        mock_fails, mock_solves, mock_flags, mock_delete_file, mock_files,
        mock_tags, mock_hints, mock_docker_challenge, mock_challenges
    ):
        """Tracker entries are deleted even when delete_container returns False."""
        from docker_challenges.models.container import DockerChallengeType

        mock_challenge = MagicMock()
        mock_challenge.id = 55

        mock_docker = MagicMock()
        mock_docker_config.query.filter_by.return_value.first.return_value = mock_docker

        entry = MagicMock()
        entry.instance_id = "cont_fail"
        mock_tracker.query.filter_by.return_value.all.return_value = [entry]
        mock_delete_container.return_value = False  # Docker deletion fails

        # Mock all the CTFd database queries
        mock_fails.query.filter_by.return_value.delete.return_value = None
        mock_solves.query.filter_by.return_value.delete.return_value = None
        mock_flags.query.filter_by.return_value.delete.return_value = None
        mock_files.query.filter_by.return_value.all.return_value = []
        mock_tags.query.filter_by.return_value.delete.return_value = None
        mock_hints.query.filter_by.return_value.delete.return_value = None
        mock_docker_challenge.query.filter_by.return_value.delete.return_value = None
        mock_challenges.query.filter_by.return_value.delete.return_value = None

        DockerChallengeType.delete(mock_challenge)

        # Tracker bulk delete must still be called
        mock_tracker.query.filter_by.assert_any_call(challenge_id=55)

    @pytest.mark.medium
    @patch("docker_challenges.models.container.Challenges")
    @patch("docker_challenges.models.container.DockerChallenge")
    @patch("docker_challenges.models.container.Hints")
    @patch("docker_challenges.models.container.Tags")
    @patch("docker_challenges.models.container.ChallengeFiles")
    @patch("docker_challenges.models.container.delete_file")
    @patch("docker_challenges.models.container.Flags")
    @patch("docker_challenges.models.container.Solves")
    @patch("docker_challenges.models.container.Fails")
    @patch("docker_challenges.models.container.db")
    @patch("docker_challenges.models.container.DockerChallengeTracker")
    @patch("docker_challenges.models.container.delete_container")
    @patch("docker_challenges.models.container.DockerConfig")
    def test_delete_skips_docker_when_no_config(
        self, mock_docker_config, mock_delete_container, mock_tracker, mock_db,
        mock_fails, mock_solves, mock_flags, mock_delete_file, mock_files,
        mock_tags, mock_hints, mock_docker_challenge, mock_challenges
    ):
        """delete() skips Docker calls gracefully when DockerConfig is not found."""
        from docker_challenges.models.container import DockerChallengeType

        mock_challenge = MagicMock()
        mock_challenge.id = 77

        mock_docker_config.query.filter_by.return_value.first.return_value = None  # No config

        entry = MagicMock()
        entry.instance_id = "cont_orphan"
        mock_tracker.query.filter_by.return_value.all.return_value = [entry]

        # Mock all the CTFd database queries
        mock_fails.query.filter_by.return_value.delete.return_value = None
        mock_solves.query.filter_by.return_value.delete.return_value = None
        mock_flags.query.filter_by.return_value.delete.return_value = None
        mock_files.query.filter_by.return_value.all.return_value = []
        mock_tags.query.filter_by.return_value.delete.return_value = None
        mock_hints.query.filter_by.return_value.delete.return_value = None
        mock_docker_challenge.query.filter_by.return_value.delete.return_value = None
        mock_challenges.query.filter_by.return_value.delete.return_value = None

        DockerChallengeType.delete(mock_challenge)

        mock_delete_container.assert_not_called()
        # Tracker delete should still be called
        mock_tracker.query.filter_by.assert_any_call(challenge_id=77)

    @pytest.mark.medium
    @patch("docker_challenges.models.container.Challenges")
    @patch("docker_challenges.models.container.DockerChallenge")
    @patch("docker_challenges.models.container.Hints")
    @patch("docker_challenges.models.container.Tags")
    @patch("docker_challenges.models.container.ChallengeFiles")
    @patch("docker_challenges.models.container.delete_file")
    @patch("docker_challenges.models.container.Flags")
    @patch("docker_challenges.models.container.Solves")
    @patch("docker_challenges.models.container.Fails")
    @patch("docker_challenges.models.container.db")
    @patch("docker_challenges.models.container.DockerChallengeTracker")
    @patch("docker_challenges.models.container.delete_container")
    @patch("docker_challenges.models.container.DockerConfig")
    def test_delete_commits_once(
        self, mock_docker_config, mock_delete_container, mock_tracker, mock_db,
        mock_fails, mock_solves, mock_flags, mock_delete_file, mock_files,
        mock_tags, mock_hints, mock_docker_challenge, mock_challenges
    ):
        """delete() calls db.session.commit() exactly once."""
        from docker_challenges.models.container import DockerChallengeType

        mock_challenge = MagicMock()
        mock_challenge.id = 10

        mock_docker = MagicMock()
        mock_docker_config.query.filter_by.return_value.first.return_value = mock_docker
        mock_tracker.query.filter_by.return_value.all.return_value = []
        mock_delete_container.return_value = True

        # Mock all the CTFd database queries
        mock_fails.query.filter_by.return_value.delete.return_value = None
        mock_solves.query.filter_by.return_value.delete.return_value = None
        mock_flags.query.filter_by.return_value.delete.return_value = None
        mock_files.query.filter_by.return_value.all.return_value = []
        mock_tags.query.filter_by.return_value.delete.return_value = None
        mock_hints.query.filter_by.return_value.delete.return_value = None
        mock_docker_challenge.query.filter_by.return_value.delete.return_value = None
        mock_challenges.query.filter_by.return_value.delete.return_value = None

        DockerChallengeType.delete(mock_challenge)

        mock_db.session.commit.assert_called_once()
