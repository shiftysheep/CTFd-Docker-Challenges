"""
Tests for port assignment functions in containers.py and services.py.

These functions assign random available ports from the range [30000, 60000)
for Docker containers and services while avoiding blocked ports.
"""

from __future__ import annotations

import random

import pytest

# Import functions after conftest stubs are loaded
from docker_challenges.functions.containers import _assign_container_ports
from docker_challenges.functions.services import _assign_service_ports

# Constants used by the functions under test
PORT_ASSIGNMENT_MIN = 30000
PORT_ASSIGNMENT_MAX = 60000
MAX_PORT_ASSIGNMENT_ATTEMPTS = 100


class TestAssignContainerPorts:
    """Tests for _assign_container_ports function."""

    @pytest.mark.light
    def test_single_port_returns_one_entry(self):
        """Single port should return dictionary with one entry."""
        result = _assign_container_ports(["80/tcp"], [])
        assert len(result) == 1
        assert next(iter(result.values())) == {}

    @pytest.mark.light
    def test_multiple_ports_returns_correct_count(self):
        """Multiple ports should return correct number of entries."""
        needed_ports = ["80/tcp", "443/tcp", "8080/tcp"]
        result = _assign_container_ports(needed_ports, [])
        assert len(result) == len(needed_ports)

    @pytest.mark.light
    def test_assigned_ports_in_valid_range(self):
        """All assigned ports should be within [30000, 60000) range."""
        needed_ports = ["80/tcp", "443/tcp", "8080/tcp", "3000/tcp"]
        result = _assign_container_ports(needed_ports, [])

        for port_str in result.keys():
            port_num = int(port_str.split("/")[0])
            assert PORT_ASSIGNMENT_MIN <= port_num < PORT_ASSIGNMENT_MAX

    @pytest.mark.light
    def test_assigned_ports_avoid_blocked_ports(self):
        """Assigned ports should not overlap with blocked_ports."""
        blocked = [30000, 30001, 30002, 40000, 50000]
        result = _assign_container_ports(["80/tcp", "443/tcp"], blocked)

        for port_str in result.keys():
            port_num = int(port_str.split("/")[0])
            assert port_num not in blocked

    @pytest.mark.light
    def test_empty_needed_ports_returns_empty_dict(self):
        """Empty needed_ports should return empty dictionary."""
        result = _assign_container_ports([], [30000, 30001])
        assert result == {}

    @pytest.mark.light
    def test_port_exhaustion_raises_runtime_error(self):
        """Port exhaustion should raise RuntimeError."""
        # Block the entire range to force exhaustion
        blocked = list(range(PORT_ASSIGNMENT_MIN, PORT_ASSIGNMENT_MAX))

        with pytest.raises(
            RuntimeError,
            match=f"Failed to find available port after {MAX_PORT_ASSIGNMENT_ATTEMPTS} attempts",
        ):
            _assign_container_ports(["80/tcp"], blocked)

    @pytest.mark.light
    def test_no_blocked_ports_works_fine(self):
        """Function should work correctly with empty blocked_ports list."""
        result = _assign_container_ports(["80/tcp", "443/tcp"], [])
        assert len(result) == 2
        for port_str in result.keys():
            port_num = int(port_str.split("/")[0])
            assert PORT_ASSIGNMENT_MIN <= port_num < PORT_ASSIGNMENT_MAX

    @pytest.mark.light
    def test_deterministic_with_seed(self):
        """Random seed should produce deterministic results."""
        random.seed(42)
        result1 = _assign_container_ports(["80/tcp", "443/tcp"], [])

        random.seed(42)
        result2 = _assign_container_ports(["80/tcp", "443/tcp"], [])

        assert result1 == result2


class TestAssignServicePorts:
    """Tests for _assign_service_ports function."""

    @pytest.mark.light
    def test_single_port_returns_one_entry(self):
        """Single port should return list with one entry."""
        result = _assign_service_ports(["80/tcp"], [])
        assert len(result) == 1
        assert result[0]["TargetPort"] == 80

    @pytest.mark.light
    def test_multiple_ports_returns_correct_count(self):
        """Multiple ports should return correct number of entries."""
        needed_ports = ["80/tcp", "443/tcp", "8080/tcp"]
        result = _assign_service_ports(needed_ports, [])
        assert len(result) == len(needed_ports)

    @pytest.mark.light
    def test_published_ports_in_valid_range(self):
        """All PublishedPort values should be within [30000, 60000) range."""
        needed_ports = ["80/tcp", "443/tcp", "8080/tcp", "3000/tcp"]
        result = _assign_service_ports(needed_ports, [])

        for port_dict in result:
            assert PORT_ASSIGNMENT_MIN <= port_dict["PublishedPort"] < PORT_ASSIGNMENT_MAX

    @pytest.mark.light
    def test_published_ports_avoid_blocked_ports(self):
        """Published ports should not overlap with blocked_ports."""
        blocked = [30000, 30001, 30002, 40000, 50000]
        result = _assign_service_ports(["80/tcp", "443/tcp"], blocked)

        for port_dict in result:
            assert port_dict["PublishedPort"] not in blocked

    @pytest.mark.light
    def test_each_entry_has_correct_keys(self):
        """Each entry should have all required keys."""
        result = _assign_service_ports(["80/tcp"], [])
        required_keys = {"PublishedPort", "PublishMode", "Protocol", "TargetPort", "Name"}

        assert len(result) == 1
        assert set(result[0].keys()) == required_keys

    @pytest.mark.light
    def test_publish_mode_is_ingress(self):
        """PublishMode should always be 'ingress'."""
        result = _assign_service_ports(["80/tcp", "443/tcp"], [])

        for port_dict in result:
            assert port_dict["PublishMode"] == "ingress"

    @pytest.mark.light
    def test_protocol_is_tcp(self):
        """Protocol should always be 'tcp'."""
        result = _assign_service_ports(["80/tcp", "443/tcp"], [])

        for port_dict in result:
            assert port_dict["Protocol"] == "tcp"

    @pytest.mark.light
    def test_target_port_parses_correctly(self):
        """TargetPort should correctly parse from port_spec."""
        test_cases = [
            ("80/tcp", 80),
            ("443/tcp", 443),
            ("8080/tcp", 8080),
            ("3000/tcp", 3000),
        ]

        for port_spec, expected_target in test_cases:
            result = _assign_service_ports([port_spec], [])
            assert result[0]["TargetPort"] == expected_target

    @pytest.mark.light
    def test_empty_needed_ports_returns_empty_list(self):
        """Empty needed_ports should return empty list."""
        result = _assign_service_ports([], [30000, 30001])
        assert result == []

    @pytest.mark.light
    def test_port_exhaustion_raises_runtime_error(self):
        """Port exhaustion should raise RuntimeError."""
        # Block the entire range to force exhaustion
        blocked = list(range(PORT_ASSIGNMENT_MIN, PORT_ASSIGNMENT_MAX))

        with pytest.raises(
            RuntimeError,
            match=f"Failed to find available port after {MAX_PORT_ASSIGNMENT_ATTEMPTS} attempts",
        ):
            _assign_service_ports(["80/tcp"], blocked)

    @pytest.mark.light
    def test_name_field_format(self):
        """Name field should follow correct format."""
        test_cases = ["80/tcp", "443/tcp", "8080/tcp"]

        for port_spec in test_cases:
            result = _assign_service_ports([port_spec], [])
            expected_name = f"Exposed Port {port_spec}"
            assert result[0]["Name"] == expected_name
