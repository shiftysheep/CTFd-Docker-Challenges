"""Tests for port extraction functions in docker_challenges.functions.general.

These tests verify the extraction logic for Docker container and service ports
without requiring Docker API connectivity or CTFd runtime dependencies.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

# Import general module directly without triggering package __init__.py
_general_path = Path(__file__).parent.parent / "docker_challenges" / "functions" / "general.py"
_spec = importlib.util.spec_from_file_location("general", _general_path)
_general_module = importlib.util.module_from_spec(_spec)
sys.modules["general"] = _general_module
_spec.loader.exec_module(_general_module)

_extract_container_ports = _general_module._extract_container_ports
_extract_service_ports = _general_module._extract_service_ports


@pytest.mark.light
class TestExtractContainerPorts:
    """Tests for _extract_container_ports function."""

    def test_extract_multiple_public_ports(self):
        """Standard container JSON with multiple ports extracts all PublicPort values."""
        containers = [
            {
                "Id": "abc123",
                "Ports": [
                    {"PrivatePort": 80, "PublicPort": 8080, "Type": "tcp"},
                    {"PrivatePort": 443, "PublicPort": 8443, "Type": "tcp"},
                ],
            }
        ]
        result = _extract_container_ports(containers)
        assert result == [8080, 8443]

    def test_skip_container_without_ports_key(self):
        """Container with no Ports key is skipped."""
        containers = [{"Id": "abc123", "Status": "running"}]
        result = _extract_container_ports(containers)
        assert result == []

    def test_skip_container_with_empty_ports_list(self):
        """Container with empty Ports list is skipped."""
        containers = [{"Id": "abc123", "Ports": []}]
        result = _extract_container_ports(containers)
        assert result == []

    def test_skip_port_with_public_port_zero(self):
        """Container with PublicPort=0 is skipped (truthy check)."""
        containers = [
            {
                "Id": "abc123",
                "Ports": [
                    {"PrivatePort": 80, "PublicPort": 0, "Type": "tcp"},
                ],
            }
        ]
        result = _extract_container_ports(containers)
        assert result == []

    def test_mixed_containers_extracts_only_with_ports(self):
        """Mixed containers: some with ports, some without - extracts only from those with ports."""
        containers = [
            {
                "Id": "container1",
                "Ports": [{"PrivatePort": 80, "PublicPort": 8080, "Type": "tcp"}],
            },
            {"Id": "container2", "Status": "running"},  # No Ports key
            {"Id": "container3", "Ports": []},  # Empty Ports
            {
                "Id": "container4",
                "Ports": [{"PrivatePort": 443, "PublicPort": 8443, "Type": "tcp"}],
            },
        ]
        result = _extract_container_ports(containers)
        assert result == [8080, 8443]

    def test_empty_container_list(self):
        """Empty container list returns empty result."""
        result = _extract_container_ports([])
        assert result == []

    def test_skip_container_with_only_private_port(self):
        """Container with only PrivatePort (no PublicPort key) is skipped."""
        containers = [
            {
                "Id": "abc123",
                "Ports": [
                    {"PrivatePort": 80, "Type": "tcp"},  # Missing PublicPort key
                ],
            }
        ]
        result = _extract_container_ports(containers)
        assert result == []


@pytest.mark.light
class TestExtractServicePorts:
    """Tests for _extract_service_ports function."""

    def test_extract_published_ports(self):
        """Standard service JSON extracts PublishedPort values."""
        services = [
            {
                "ID": "svc123",
                "Endpoint": {
                    "Spec": {
                        "Ports": [
                            {
                                "Protocol": "tcp",
                                "TargetPort": 80,
                                "PublishedPort": 8080,
                                "PublishMode": "ingress",
                            },
                            {
                                "Protocol": "tcp",
                                "TargetPort": 443,
                                "PublishedPort": 8443,
                                "PublishMode": "ingress",
                            },
                        ]
                    }
                },
            }
        ]
        result = _extract_service_ports(services)
        assert result == [8080, 8443]

    def test_skip_service_without_endpoint(self):
        """Service with no Endpoint key is skipped."""
        services = [{"ID": "svc123", "Spec": {"Name": "web"}}]
        result = _extract_service_ports(services)
        assert result == []

    def test_skip_service_with_endpoint_but_no_spec(self):
        """Service with Endpoint but no Spec is skipped."""
        services = [{"ID": "svc123", "Endpoint": {"VirtualIPs": []}}]
        result = _extract_service_ports(services)
        assert result == []

    def test_skip_service_with_spec_but_no_ports(self):
        """Service with Spec but no Ports key is skipped."""
        services = [{"ID": "svc123", "Endpoint": {"Spec": {"Mode": "vip"}}}]
        result = _extract_service_ports(services)
        assert result == []

    def test_empty_service_list(self):
        """Empty service list returns empty result."""
        result = _extract_service_ports([])
        assert result == []

    def test_mixed_services_extracts_only_with_ports(self):
        """Mixed services: some with ports, some without - extracts only from those with ports."""
        services = [
            {
                "ID": "svc1",
                "Endpoint": {
                    "Spec": {
                        "Ports": [
                            {
                                "Protocol": "tcp",
                                "TargetPort": 80,
                                "PublishedPort": 8080,
                                "PublishMode": "ingress",
                            }
                        ]
                    }
                },
            },
            {"ID": "svc2", "Spec": {"Name": "db"}},  # No Endpoint
            {"ID": "svc3", "Endpoint": {"VirtualIPs": []}},  # No Spec
            {
                "ID": "svc4",
                "Endpoint": {
                    "Spec": {
                        "Ports": [
                            {
                                "Protocol": "tcp",
                                "TargetPort": 443,
                                "PublishedPort": 8443,
                                "PublishMode": "ingress",
                            }
                        ]
                    }
                },
            },
        ]
        result = _extract_service_ports(services)
        assert result == [8080, 8443]
