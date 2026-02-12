# Deployment Constraints

This document covers ONLY architectural constraints affecting deployment, not deployment procedures.

## Deployment Constraints

**Single Docker Host Architecture**: Plugin designed for single Docker API endpoint

- `DockerConfig` model stores one configuration (id=1)
- Not designed for multi-host load balancing or geographic distribution
- All challenges run on same Docker host

**Docker API Accessibility**: Docker API must be accessible via HTTP/HTTPS from CTFd instance

- TLS certificates stored as temporary files in `/tmp` with 0o600 permissions
- Certificate validation requires file paths (Docker Python SDK limitation)

**Port Range Constraint**: Container port allocation restricted to 30000-60000

- Production constraint to avoid system service conflicts
- Requires 30000 ports available on Docker host
- Port exhaustion possible with >30000 concurrent containers (unlikely in CTF)

**Plugin Directory Name**: Must be installed as `CTFd/CTFd/plugins/docker_challenges`

- Exact name required by CTFd plugin discovery
- Hyphen vs underscore matters

**Database Requirements**: Requires MariaDB or MySQL (via CTFd)

- Plugin uses CTFd's database connection
- No additional database configuration needed

**Python Module Caching**: Container restart required after Python code changes

- Flask/Werkzeug caches modules in memory
- Affects deployment workflows (cannot hot-reload Python changes)
