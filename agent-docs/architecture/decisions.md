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
