# Development Setup Backstory

This document covers ONLY non-standard setup aspects. For complete setup procedures, see `CONTRIBUTING.md`.

## Setup Backstory

**Plugin Directory Name**: Must be exactly `docker_challenges` (underscore, not hyphen) in `CTFd/CTFd/plugins/` directory

- CTFd plugin discovery requires exact name match
- Installation fails silently if directory name doesn't match

**CTFd Version Constraint**: Requires CTFd 3.8.0+ for list-based `config.json` support

- CTFd 2.3.3 has `get_configurable_plugins` bug that breaks admin menu items
- Fixed in CTFd 3.2.1+, but 3.8.0+ recommended for core theme compatibility

**Alpine.js and Bootstrap 5**: Plugin requires CTFd core theme (not legacy theme)

- v3.0.0+ uses Alpine.js for reactive components (status polling)
- Bootstrap 5 for styling (tooltips removed due to unavailability)

**Docker API Accessibility**: Must be accessible via HTTP or HTTPS from CTFd container

- TLS certificates stored in `/tmp` with 0o600 permissions (automatic)
- Configuration at `/admin/docker_config` after installation

**Development Port Mapping**: CTFd runs on port 8000 inside container, exposed via nginx on port 80

- Access local development at `http://localhost` (not `http://localhost:8000`)
- See `docker-compose.yml` for nginx configuration

**Pre-commit Hooks**: Enforces code quality automatically (Ruff, Xenon, Vulture, Bandit, Prettier)

- Hooks run on every commit, rejecting commits that fail checks
- Install hooks: `pre-commit install` after cloning repository

**Python Module Caching**: Flask/Werkzeug caches Python modules in memory

- Changes to Python code require container restart: `docker compose restart ctfd`
- JavaScript changes take effect immediately (browser cache only)
- After Python changes: (1) Restart container, (2) Wait 5-10 seconds, (3) Hard refresh browser
