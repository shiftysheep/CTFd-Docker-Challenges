"""
Tests for docker_challenges.validators module.

Tests validation functions for Docker challenge configuration,
focusing on pure validation logic without external dependencies.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

# Import validators module directly without triggering package __init__.py
_validators_path = Path(__file__).parent.parent / "docker_challenges" / "validators.py"
_spec = importlib.util.spec_from_file_location("validators", _validators_path)
_validators_module = importlib.util.module_from_spec(_spec)
sys.modules["validators"] = _validators_module
_spec.loader.exec_module(_validators_module)

validate_exposed_ports = _validators_module.validate_exposed_ports


class TestValidateExposedPorts:
    """Tests for validate_exposed_ports() function."""

    @pytest.mark.pure
    @pytest.mark.parametrize(
        "ports_string",
        [
            "80/tcp",
            "443/tcp",
            "8080/tcp",
            "3000/tcp",
        ],
    )
    def test_valid_single_port(self, ports_string: str) -> None:
        """Valid single port should not raise exception."""
        validate_exposed_ports(ports_string)

    @pytest.mark.pure
    def test_valid_multiple_ports(self) -> None:
        """Valid multiple ports should not raise exception."""
        validate_exposed_ports("80/tcp,443/tcp,8080/tcp")

    @pytest.mark.pure
    @pytest.mark.parametrize(
        "ports_string",
        [
            "53/udp",
            "123/udp",
            "514/udp",
        ],
    )
    def test_valid_udp_port(self, ports_string: str) -> None:
        """Valid UDP ports should not raise exception."""
        validate_exposed_ports(ports_string)

    @pytest.mark.pure
    def test_valid_mixed_protocols(self) -> None:
        """Mixed TCP and UDP protocols should be valid."""
        validate_exposed_ports("80/tcp,443/tcp,53/udp,123/udp")

    @pytest.mark.pure
    @pytest.mark.parametrize(
        "ports_string",
        [
            "80/TCP",
            "80/Tcp",
            "80/tCP",
            "443/UDP",
            "443/Udp",
            "443/uDp",
        ],
    )
    def test_case_insensitivity(self, ports_string: str) -> None:
        """Protocol specification should be case insensitive."""
        validate_exposed_ports(ports_string)

    @pytest.mark.pure
    @pytest.mark.parametrize(
        "ports_string",
        [
            " 80/tcp",
            "80/tcp ",
            " 80/tcp ",
            "80/tcp, 443/tcp",
            " 80/tcp , 443/tcp ",
            "  80/tcp  ,  443/tcp  ",
        ],
    )
    def test_whitespace_handling(self, ports_string: str) -> None:
        """Whitespace around entries should be trimmed."""
        validate_exposed_ports(ports_string)

    @pytest.mark.pure
    def test_boundary_port_minimum(self) -> None:
        """Port 1 (minimum valid) should be accepted."""
        validate_exposed_ports("1/tcp")

    @pytest.mark.pure
    def test_boundary_port_maximum(self) -> None:
        """Port 65535 (maximum valid) should be accepted."""
        validate_exposed_ports("65535/tcp")

    @pytest.mark.pure
    def test_empty_string_raises_error(self) -> None:
        """Empty string should raise ValueError."""
        with pytest.raises(ValueError, match="At least one exposed port must be configured"):
            validate_exposed_ports("")

    @pytest.mark.pure
    def test_none_raises_error(self) -> None:
        """None input should raise ValueError."""
        with pytest.raises(ValueError, match="At least one exposed port must be configured"):
            validate_exposed_ports(None)  # type: ignore[arg-type]

    @pytest.mark.pure
    @pytest.mark.parametrize(
        "ports_string",
        [
            " ",
            "  ",
            "\t",
            "\n",
            "   \t\n   ",
        ],
    )
    def test_whitespace_only_raises_error(self, ports_string: str) -> None:
        """Whitespace-only strings should raise ValueError."""
        with pytest.raises(ValueError, match="At least one exposed port must be configured"):
            validate_exposed_ports(ports_string)

    @pytest.mark.pure
    @pytest.mark.parametrize(
        "ports_string",
        [
            "80",
            "443",
            "8080",
        ],
    )
    def test_missing_protocol_raises_error(self, ports_string: str) -> None:
        """Port without protocol should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid port format"):
            validate_exposed_ports(ports_string)

    @pytest.mark.pure
    @pytest.mark.parametrize(
        "ports_string",
        [
            "tcp/80",
            "udp/53",
            "tcp:80",
            "80-tcp",
            "80_tcp",
        ],
    )
    def test_invalid_format_no_slash_raises_error(self, ports_string: str) -> None:
        """Invalid format without proper slash delimiter should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid port format"):
            validate_exposed_ports(ports_string)

    @pytest.mark.pure
    @pytest.mark.parametrize(
        "ports_string",
        [
            "80/http",
            "443/https",
            "53/dns",
            "80/sctp",
            "80/icmp",
            "80/",
            "/tcp",
        ],
    )
    def test_invalid_protocol_raises_error(self, ports_string: str) -> None:
        """Invalid protocol should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid port format"):
            validate_exposed_ports(ports_string)

    @pytest.mark.pure
    def test_port_zero_raises_error(self) -> None:
        """Port 0 (out of range) should raise ValueError."""
        with pytest.raises(ValueError, match="Port number 0 is out of valid range"):
            validate_exposed_ports("0/tcp")

    @pytest.mark.pure
    def test_port_above_maximum_raises_error(self) -> None:
        """Port 65536 (out of range) should raise ValueError."""
        with pytest.raises(ValueError, match="Port number 65536 is out of valid range"):
            validate_exposed_ports("65536/tcp")

    @pytest.mark.pure
    def test_port_far_above_maximum_raises_error(self) -> None:
        """Port 99999 (out of range) should raise ValueError."""
        with pytest.raises(ValueError, match="Port number 99999 is out of valid range"):
            validate_exposed_ports("99999/tcp")

    @pytest.mark.pure
    @pytest.mark.parametrize(
        "ports_string",
        [
            "-1/tcp",
            "-80/tcp",
            "-443/tcp",
        ],
    )
    def test_negative_port_raises_error(self, ports_string: str) -> None:
        """Negative port numbers should raise ValueError due to invalid format."""
        with pytest.raises(ValueError, match="Invalid port format"):
            validate_exposed_ports(ports_string)

    @pytest.mark.pure
    @pytest.mark.parametrize(
        "ports_string,expected_error",
        [
            ("80/tcp,invalid", "Invalid port format: 'invalid'"),
            ("80/tcp,443", "Invalid port format: '443'"),
            ("80/tcp,99999/tcp", "Port number 99999 is out of valid range"),
            ("80/tcp,0/tcp", "Port number 0 is out of valid range"),
            ("80/tcp,443/http", "Invalid port format: '443/http'"),
        ],
    )
    def test_mixed_valid_invalid_raises_error(self, ports_string: str, expected_error: str) -> None:
        """Mixed valid and invalid entries should raise ValueError on first invalid."""
        with pytest.raises(ValueError, match=expected_error):
            validate_exposed_ports(ports_string)

    @pytest.mark.pure
    def test_all_empty_entries_after_split_raises_error(self) -> None:
        """String with only empty entries after split should raise ValueError."""
        with pytest.raises(ValueError, match="At least one valid port must be configured"):
            validate_exposed_ports(",,,")

    @pytest.mark.pure
    def test_empty_entries_mixed_with_valid(self) -> None:
        """Empty entries mixed with valid ports should be filtered out."""
        validate_exposed_ports("80/tcp,,443/tcp,")
        validate_exposed_ports(",80/tcp,443/tcp")
        validate_exposed_ports("80/tcp, ,443/tcp")
