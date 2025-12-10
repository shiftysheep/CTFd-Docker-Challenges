"""
Configuration constants for Docker challenge plugin.

These values control timeouts, port assignment ranges, and other configurable
behavior across the plugin.
"""

# Container lifecycle timeouts (in seconds)
CONTAINER_STALE_TIMEOUT_SECONDS = 7200  # 2 hours - auto-cleanup threshold
CONTAINER_REVERT_TIMEOUT_SECONDS = 300  # 5 minutes - minimum time before revert allowed

# Port assignment range for Docker containers/services
PORT_ASSIGNMENT_MIN = 30000  # Minimum port for random assignment
PORT_ASSIGNMENT_MAX = 60000  # Maximum port for random assignment
