# CTFd Docker Challenges Plugin

**What**: CTFd plugin for Docker-based CTF challenges using Flask, SQLAlchemy, Alpine.js, and Docker API.

**Why**: Enables isolated per-user/team Docker containers for CTF challenges with automated lifecycle management (5-min revert, 2-hour cleanup). Alpine.js chosen for lightweight reactive status polling without framework overhead. Polymorphic challenge types extend CTFd's base model for seamless integration.

See [architecture overview](agent-docs/architecture/overview.md) for system design and [architecture decisions](agent-docs/architecture/decisions.md) for key technical choices.

## Quick Start

```bash
docker compose up  # Start CTFd on :8000 with Docker-in-Docker test environment
```

See [setup guide](agent-docs/development/setup.md) for complete environment configuration and Docker API connectivity.

## Development

```bash
pre-commit run --all-files  # Run code quality checks (Ruff, Xenon, Vulture, Bandit, Prettier)
pytest tests/               # Run test suite (manual testing via docker compose)
```

**Key Constraints**:

- Plugin must install as `CTFd/CTFd/plugins/docker_challenges` (exact name required)
- Python changes require `docker compose restart ctfd` + hard browser refresh (module caching)
- Challenge views use global scope JavaScript (avoid ES6 modules - Alpine.js race conditions)
- Always filter `DockerChallengeTracker` by both `challenge_id` AND `docker_image`
- Docker secrets require both HTTPS (browser) and Docker TLS (Docker API) — see agent-docs/architecture/decisions.md

**Resources**:

- [Architecture patterns](agent-docs/architecture/patterns.md) - Design patterns and conventions
- [Known limitations](agent-docs/architecture/limitations.md) - Documented issues and workarounds
- [Testing guide](agent-docs/development/testing.md) - Manual testing checklist and Docker Compose workflow
- [Build process](agent-docs/development/building.md) - UV package manager, Hatchling, pre-commit hooks
- [Deployment constraints](agent-docs/development/deployment.md) - Port range, Docker API access, plugin naming

**Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md) for code quality standards, commit conventions (Commitizen), and PR process.
