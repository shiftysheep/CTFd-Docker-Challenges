# Key Architectural Decisions

This document summarizes major architectural decisions made in the CTFd-Docker-Challenges plugin. These decisions have significant implications for development, maintenance, and future enhancements.

## JavaScript Architecture: Global Scope for Challenge Views

**Decision**: Use global scope functions in `view.js` instead of ES6 modules
**Rationale**: CTFd loads challenge views dynamically via AJAX with `getScript()`. ES6 modules load asynchronously, creating race conditions when Alpine.js parses the DOM before modules finish loading. Global scope functions are immediately available when Alpine.js initializes.
**Impact**: Admin forms can use ES6 modules (full page loads), but player challenge views must expose functions to `window` scope.
**Reference**: `CLAUDE.md` - "Frontend Architecture - Keep It Simple"

## Port Range: 30000-60000

**Decision**: Random port allocation restricted to 30000-60000 range
**Rationale**: Production constraint to avoid conflicts with system services (0-1023), common applications (1024-29999), and provide sufficient range for concurrent challenges (30000 ports available).
**Impact**: Port exhaustion possible with >30000 concurrent containers (unlikely in CTF environment).
**Reference**: `functions/containers.py:19-40`, `functions/services.py:18-29`

## Polymorphic Challenge Types over Feature Flags

**Decision**: Use SQLAlchemy polymorphic inheritance for container vs service challenges
**Rationale**: Seamless integration with CTFd's challenge system. Polymorphic types allow different models, forms, and lifecycle logic while maintaining compatibility with CTFd's queries, admin interface, and scoring.
**Impact**: Two separate models (`DockerChallenge`, `DockerServiceChallenge`) and type implementations, but cleaner separation of concerns.
**Reference**: `models/models.py`, `models/container.py`, `models/service.py`

## Single-Row Config Pattern

**Decision**: Store Docker API config in single database row (`DockerConfig.id = 1`)
**Rationale**: Simple, predictable retrieval without environment variables or config files. Allows runtime changes via admin interface without container restarts.
**Impact**: Not designed for multi-Docker-host scenarios (single host per CTFd instance).
**Reference**: `models/models.py:DockerConfig`, retrieval pattern `DockerConfig.query.filter_by(id=1).first()`

## TLS Certificates as Temporary Files

**Decision**: Store TLS certs in `/tmp` directory with 0o600 permissions
**Rationale**: Docker Python SDK requires file paths for certificate validation, database storage requires conversion to temporary files anyway. Ephemeral storage acceptable for runtime-only use.
**Impact**: Certs recreated from database on every request, minimal performance overhead.
**Reference**: `functions/general.py:do_request()`

## Tracker Query Pattern: challenge_id AND docker_image

**Decision**: Always filter `DockerChallengeTracker` by BOTH `challenge_id` AND `docker_image`
**Rationale**: Challenge IDs can be reused if challenges deleted/recreated. Docker image provides additional uniqueness guarantee. Prevents tracker collisions.
**Impact**: All tracker queries must include both fields.
**Reference**: `api/api.py` query patterns, `CLAUDE.md` - "Database Queries"

## Container Naming: Image + MD5 Hash

**Decision**: Container names formatted as `{image}_{md5(team)[:10]}`
**Rationale**: Deterministic naming for debugging, team isolation without exposing team IDs, avoids collisions with sanitized special characters.
**Impact**: Predictable naming pattern for troubleshooting, but breaks if team hashes collide (extremely unlikely).
**Reference**: `functions/containers.py`, `functions/services.py`

## Image Tag Selection: First in RepoTags

**Decision**: Read first tag in Docker image `RepoTags` array
**Rationale**: Docker images can have multiple tags pointing to same image ID. Plugin needs deterministic selection for storage and display.
**Impact**: Users must ensure desired tag is listed first, or manually alias images.
**Reference**: `functions/general.py:get_repositories()`, `CLAUDE.md` - "Docker tag aliasing"

## Automatic Cleanup Timers

**Decision**: 5-minute revert timer, 2-hour stale cleanup, solve cleanup
**Rationale**: Balance between user experience (rapid iteration) and resource management (prevent exhaustion). 5 minutes allows quick troubleshooting, 2 hours prevents abandoned containers.
**Impact**: Users cannot revert containers immediately (5-min wait), but automatic cleanup prevents admin intervention.
**Reference**: `api/api.py:110`, `models/container.py:177`, `models/service.py:187`

## Configurable Exposed Ports (v3.0.0)

**Decision**: Allow challenge admins to configure exposed ports, merging with image metadata
**Rationale**: Some Docker images lack ExposedPorts metadata (e.g., Alpine Linux), others expose ports not needed for challenge. Admin control provides flexibility.
**Impact**: Additional UI complexity (port management in admin forms), but resolves KeyError crashes with minimal-config images.
**Reference**: `assets/shared/portManagement.js`, `functions/general.py:get_required_ports()`

## UV over pip/Poetry

**Decision**: Use UV for dependency management and packaging
**Rationale**: Faster dependency resolution, modern PEP 621 pyproject.toml support, built-in virtual environment management.
**Impact**: Contributors must install UV, but development workflow streamlined.
**Reference**: `pyproject.toml`, `CONTRIBUTING.md`

## Ruff over Black/flake8/isort

**Decision**: Single tool (Ruff) for linting and formatting
**Rationale**: Replaces three tools (Black, isort, flake8) with faster, Rust-based implementation. 100-character line length modern standard.
**Impact**: Simpler pre-commit configuration, faster CI/CD checks.
**Reference**: `pyproject.toml`, `.pre-commit-config.yaml`

## Commitizen for Conventional Commits

**Decision**: Enforce conventional commits with Commitizen
**Rationale**: Automated changelog generation, semantic versioning, consistent commit history for project tracking.
**Impact**: Contributors must format commit messages per convention or pre-commit hook fails.
**Reference**: `pyproject.toml:tool.commitizen`, `CONTRIBUTING.md`

## Secrets Transmission Security

**Decision**: Require both HTTPS (browser↔server) and Docker TLS (server↔Docker API) before allowing secret creation.

**Rationale**: Secrets traverse two network legs — the browser submitting the secret value to CTFd, and CTFd forwarding the value to the Docker daemon. HTTPS encrypts the first leg and Docker TLS encrypts the second. If either leg is unencrypted, an attacker performing a man-in-the-middle attack on that segment could capture secret values in plaintext. Enforcing both layers ensures end-to-end encryption of secret material across the entire transmission path.

**Attack vectors prevented**:

- **Browser↔Server (no HTTPS)**: An attacker on the network between the admin's browser and the CTFd server intercepts the POST request containing the secret value.
- **Server↔Docker API (no TLS)**: An attacker on the network between the CTFd server and the Docker daemon intercepts the API call containing the secret value.

**Admin configuration**: Administrators must enable HTTPS on the CTFd instance AND configure TLS on the Docker daemon for secrets functionality to work. If either encryption layer is missing, the API rejects secret creation with HTTP 400 and a descriptive error message explaining which layers are required.

**Audit logging**: Secret names are logged with the acting admin's username for audit trails, but secret values are never logged to prevent credential exposure in log files.

**Reference**: `api/api.py:474-496` — `SecretAPI.post()` checks `docker.tls_enabled` and `request.is_secure` before proceeding

## Per-Secret JSON Format over CSV + Global Boolean

**Decision**: Store Docker secrets as JSON array `[{"id":"...","protected":true/false}]` instead of CSV string + global `protect_secrets` boolean.

**Rationale**: The original design applied a single file permission (0o600 or 0o777) to all secrets attached to a service challenge. In practice, some secrets (like database passwords) need restricted permissions while others (like API configuration) can be world-readable. Per-secret control requires encoding protection state alongside each secret ID.

**Alternatives considered**:

- **CSV + per-secret columns**: Would require a separate join table — overengineered for the use case.
- **CSV with backwards compatibility**: Parsing CSV fallback adds complexity and testing burden for a format that should be migrated away from.

**Format**: `docker_secrets` column stores `'[{"id":"secret_abc","protected":true},{"id":"secret_def","protected":false}]'` (JSON string, max 4096 chars). Parsed by `_parse_docker_secrets()` in `functions/services.py`.

**Breaking change**: No backwards compatibility with CSV format. Existing service challenges must be deleted and recreated after upgrade. The `protect_secrets` column remains in SQLite (no column drops) but is no longer read or written.

**Impact**: Frontend uses a list-based UI with per-secret "Protected" checkboxes instead of a multi-select dropdown + global checkbox. Hidden input serializes the JSON array on form submission.

**Reference**: `functions/services.py:_parse_docker_secrets()`, `models/models.py:DockerServiceChallenge`, `assets/shared/secretManagement.js`, commit `e594a8c`
