"""
Validation utilities for Docker challenge configuration.

This module provides shared validation functions used across different
challenge types (container and service challenges).
"""

import re


def validate_exposed_ports(ports_string: str) -> None:
    """
    Validate exposed ports format and values.

    Args:
        ports_string: Comma-separated string of ports (e.g., "80/tcp,443/tcp,53/udp")

    Raises:
        ValueError: If validation fails with descriptive error message

    Examples:
        >>> validate_exposed_ports("80/tcp,443/tcp")  # Valid
        >>> validate_exposed_ports("8080/udp")  # Valid
        >>> validate_exposed_ports("99999/tcp")  # Raises ValueError
        >>> validate_exposed_ports("")  # Raises ValueError
    """
    if not ports_string or not ports_string.strip():
        raise ValueError(
            "At least one exposed port must be configured. "
            "Please add a port in the format: port/protocol (e.g., 80/tcp)"
        )

    # Pattern matches: port/protocol where port is 1-65535, protocol is tcp/udp
    port_pattern = re.compile(r"^(\d+)/(tcp|udp)$", re.IGNORECASE)

    ports = ports_string.split(",")
    valid_ports = []

    for port_entry in ports:
        port_str = port_entry.strip()
        if not port_str:
            continue

        match = port_pattern.match(port_str)
        if not match:
            raise ValueError(
                f"Invalid port format: '{port_str}'. "
                "Expected format: port/protocol (e.g., 80/tcp, 443/tcp, 53/udp)"
            )

        port_num = int(match.group(1))
        if port_num < 1 or port_num > 65535:
            raise ValueError(
                f"Port number {port_num} is out of valid range. "
                "Port numbers must be between 1 and 65535."
            )

        valid_ports.append(port_str)

    if not valid_ports:
        raise ValueError(
            "At least one valid port must be configured. "
            "Ports must be in the format: port/protocol (e.g., 80/tcp)"
        )
