# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Pre-commit hooks with Ruff, Xenon, Vulture, Bandit, and Prettier
- Commitizen for conventional commits and automated changelog management
- pyproject.toml with Ruff configuration for Python code quality
- Configurable exposed ports feature for Docker challenges
    - Advanced Settings UI section with dynamic port management
    - Support for TCP/UDP protocol selection with port validation (1-65535)
    - Auto-population of ports from Docker image metadata
    - Multi-hook validation with visual feedback

### Changed

- Migrated from Black/isort/flake8 to Ruff for faster linting and formatting

## [1.0.0] - 2024-12-09

### Added

- Initial release of CTFd Docker Challenges plugin
- Support for Docker container and Docker Swarm service challenges
- Automatic container lifecycle management with revert timers
- Docker secrets support for service challenges
- Admin interface for Docker configuration and status monitoring
- Port assignment system with conflict avoidance (ports 30000-60000)
- 2-hour auto-cleanup for stale containers
- Container deletion on challenge solve

[unreleased]: https://github.com/shiftysheep/CTFd-Docker-Challenges/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/shiftysheep/CTFd-Docker-Challenges/releases/tag/v1.0.0
