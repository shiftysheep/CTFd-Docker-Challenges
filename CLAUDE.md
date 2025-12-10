# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

CTFd Docker Plugin adds Docker-based challenge support to CTFd (Capture The Flag platform). Players can launch isolated Docker containers/services for challenges, with automatic lifecycle management including revert timers and cleanup.

## Development Setup

**For comprehensive development guidelines**, see [CONTRIBUTING.md](CONTRIBUTING.md)

### Requirements

- Python 3.9+ with `flask_wtf` installed (`pip install flask_wtf`)
- CTFd 3.8.0+ (v3.0.0 requires core theme with Alpine.js and Bootstrap 5)
- Docker API accessible via HTTP or TLS
- Modern browser (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+)
- Pre-commit hooks (enforced code quality)
- Commitizen (conventional commits)

### Installation

The plugin must be installed as `CTFd/CTFd/plugins/docker_challenges` (exact name required). After installation:

1. Configure Docker API connection at `/admin/docker_config`
2. Select repositories to use for challenges
3. Create challenges with type `docker` or `docker_service`

### Running Development Environment

```bash
docker compose up
```

- CTFd runs on port 8000 (via container), exposed through nginx on port 80
- MariaDB database with user/pass: ctfd/ctfd
- Redis cache for session management

Common commands:

```bash
docker compose up -d        # Start in detached mode
docker compose down         # Stop and remove containers
docker compose logs -f      # Follow logs
docker compose restart ctfd # Restart CTFd service
```

## Architecture

### Challenge Types

**Two distinct challenge types registered in `__init__.py`:**

1. **`docker`** (Standard Containers)
    - Model: `DockerChallenge` ([models/models.py](docker_challenges/models/models.py))
    - Type Implementation: `DockerChallengeType` ([models/container.py](docker_challenges/models/container.py))
    - Creates standalone Docker containers via `/containers` API
    - Port binding: Random ports 30000-60000 assigned to exposed container ports
    - Lifecycle: Created via [functions/containers.py](docker_challenges/functions/containers.py)

2. **`docker_service`** (Docker Swarm Services)
    - Model: `DockerServiceChallenge` ([models/models.py](docker_challenges/models/models.py))
    - Type Implementation: `DockerServiceChallengeType` ([models/service.py](docker_challenges/models/service.py))
    - Creates Docker swarm services via `/services` API
    - Supports Docker secrets with configurable permissions (0o600 or 0o777)
    - Lifecycle: Created via [functions/services.py](docker_challenges/functions/services.py)

### Container Lifecycle Management

**Tracking System:**

- `DockerChallengeTracker` model stores active containers/services per user/team
- Tracks: instance_id, ports, host, timestamps, challenge_id, docker_image

**Automatic Cleanup Rules:**

1. **5-minute revert timer**: Players can revert (delete/recreate) their container after 5 minutes
2. **2-hour stale cleanup**: Containers older than 2 hours are auto-deleted ([api/api.py:110](docker_challenges/api/api.py#L110))
3. **Solve cleanup**: Container deleted when challenge is solved ([models/container.py:177](docker_challenges/models/container.py#L177), [models/service.py:187](docker_challenges/models/service.py#L187))

### API Structure

**REST API Namespaces** (registered in `__init__.py`):

- `/api/v1/docker` - Fetch available Docker images (admin)
- `/api/v1/container` - Create/revert containers (authenticated users)
- `/api/v1/docker_status` - Get user's active containers
- `/api/v1/nuke` - Admin endpoint to kill containers (single or all)
- `/api/v1/secret` - Fetch Docker secrets for service challenges (admin)
- `/api/v1/image_ports` - Fetch exposed ports from Docker image metadata (admin)

All API implementations in [api/api.py](docker_challenges/api/api.py)

### Docker API Communication

**Connection Handler:** [functions/general.py](docker_challenges/functions/general.py)

- `do_request()`: Centralized HTTP/HTTPS requests to Docker API
- Supports both plain HTTP and TLS with client certificate validation
- Config stored in `DockerConfig` model (one row, id=1)
- TLS certs stored as temporary files in `/tmp`

**Key Functions:**

- `get_repositories()`: List available images/repositories (inspects first tag in RepoTags array)
- `get_required_ports()`: Merge ExposedPorts from image metadata with challenge-configured ports (gracefully handles images without exposed ports)
- `get_unavailable_ports()`: Scan existing containers/services for port conflicts
- `get_secrets()`: List Docker swarm secrets

### Configurable Exposed Ports Feature

**Added in v3.0.0** - Challenge admins can configure exposed ports in Advanced Settings:

**Frontend** ([assets/\*.html](docker_challenges/assets/), [assets/\*.js](docker_challenges/assets/)):

- Collapsible "Advanced Settings" section in challenge create/update forms
- Dynamic port management UI with add/remove functionality
- TCP/UDP protocol selector and port number input (validated 1-65535)
- Auto-population: Ports fetch from `/api/v1/image_ports` when image selected
- Multi-hook validation: Capture phase + button click listeners ensure at least one port configured

**Backend**:

- Database: `exposed_ports` TEXT column in both `DockerChallenge` and `DockerServiceChallenge` models
- API: `/api/v1/image_ports` endpoint returns ports from image ExposedPorts metadata
- Logic: `get_required_ports()` merges image ports with challenge-configured ports
- Format: Comma-separated `port/protocol` (e.g., "80/tcp,443/tcp,53/udp")

**Behavior**:

- Image metadata ports auto-populate when image selected
- Additional ports can be added manually
- Challenge ports override/supplement image ports
- Handles images without ExposedPorts (e.g., Alpine Linux)

### Port Assignment Strategy

Random port allocation to avoid conflicts:

1. Merge container's exposed ports (image metadata + challenge configuration)
2. Query all active containers/services for used ports
3. Randomly select from range 30000-60000, excluding blocked ports
4. Assign to container/service PortBindings/PublishedPort

Implementation: [functions/containers.py:19-40](docker_challenges/functions/containers.py#L19-L40), [functions/services.py:18-29](docker_challenges/functions/services.py#L18-L29)

### Database Models

**Core Models** ([models/models.py](docker_challenges/models/models.py)):

- `DockerConfig`: Single-row config (hostname, TLS settings, repositories)
- `DockerChallenge`: Polymorphic challenge type extending CTFd's `Challenges` (includes `exposed_ports` TEXT column)
- `DockerServiceChallenge`: Polymorphic type for services with secrets support (includes `exposed_ports` TEXT column)
- `DockerChallengeTracker`: Per-user/team active container tracking

**Polymorphic Identity:**

- Uses SQLAlchemy polymorphic inheritance from CTFd's base `Challenges` model
- Allows seamless integration with CTFd's challenge system

### Challenge Type Integration

Both challenge types implement CTFd's `BaseChallenge` interface:

- `create()`: Initialize challenge from admin form
- `read()`: Serialize challenge data for frontend
- `update()`: Modify existing challenge
- `delete()`: Cleanup challenge and kill all associated containers
- `attempt()`: Validate flag submission
- `solve()`: Record solve and cleanup container
- `fail()`: Record failed attempt

### Admin Views

**Two admin blueprints** ([**init**.py](docker_challenges/__init__.py)):

1. `/admin/docker_config`: Configure Docker connection, select repositories
2. `/admin/docker_status`: View all active containers across teams/users

Configuration menu items defined in [config.json](docker_challenges/config.json)

## Code Quality & Development Tools

**Added in v3.0.0+**:

- **Pre-commit hooks**: Automated code quality enforcement on every commit
- **Ruff**: Python linting and formatting (replaces Black, isort, flake8) - 100 char line length
- **Xenon**: Code complexity monitoring (max: B absolute/modules, A average)
- **Vulture**: Dead code detection (80% confidence threshold)
- **Bandit**: Security vulnerability scanning
- **Prettier**: JavaScript/HTML/CSS/Markdown formatting
- **Commitizen**: Conventional commit enforcement and changelog automation
- **PEP 621**: Modern pyproject.toml configuration with version management

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed code quality standards.

## Known Issues & Bug Fixes

### Fixed in v3.0.0

- **Dynamic form loading** (JavaScript): Challenge forms load dynamically, removed DOMContentLoaded wrappers that prevented API calls
- **Bootstrap tooltips** (JavaScript): Removed tooltip initialization - `bootstrap` not exposed as global in core theme
- **ExposedPorts KeyError** (Python): Resolved with configurable exposed ports feature - admins can now define ports per challenge, auto-populated from image metadata

### Outstanding Issues

- **Timeout failure bug** ([api/api.py:112](docker_challenges/api/api.py#L112)): Cleanup failures prevent new container launches
- Need autocreate connection info based on service type
- Would like dynamic port pointing and individual secret permissions
- Docker tag aliasing: Plugin reads first tag in RepoTags array, images must have desired tag as primary tag

## CTFd Integration Notes

**Required CTFd modification** (for CTFd 2.3.3, resolved in 3.2.1+):

- `get_configurable_plugins` function must support list-based `config.json` format
- See: https://github.com/CTFd/CTFd/issues/1370

**Challenge naming convention:**

- Images stored by repository tags: `org/repo:tag`
- Example: `stormctf/infosecon2019:arbit`
- Container names: `{image}_{md5(team)[:10]}` (sanitized, underscores replace special chars)

## Working with the Code

### Adding Features

1. New API endpoints: Add namespace to [api/api.py](docker_challenges/api/api.py), register in `__init__.py:load()`
2. New challenge types: Extend `BaseChallenge`, create model with polymorphic identity
3. Container lifecycle changes: Modify [functions/containers.py](docker_challenges/functions/containers.py) or [functions/services.py](docker_challenges/functions/services.py)

### Testing Container Creation

- Check logs for Docker API requests at INFO level ([functions/general.py:44](docker_challenges/functions/general.py#L44))
- Container creation returns `(instance_id, data)` tuple - verify instance_id is not None
- Port conflicts will cause random reassignment attempts in while loop

### Database Queries

- Teams mode check: `is_teams_mode()` determines whether to use `team_id` or `user_id`
- Always filter tracker by both challenge_id and docker_image to find user's specific instance
- `DockerConfig.query.filter_by(id=1).first()` is the standard config retrieval pattern

### JavaScript/Frontend Development

**Script Loading Architecture:**

CTFd challenge types use a `scripts` dictionary to specify JavaScript files loaded via jQuery's `getScript()` mechanism:

```python
# In models/container.py and models/service.py
scripts = {
    "create": "/plugins/docker_challenges/assets/stub_create.js",
    "update": "/plugins/docker_challenges/assets/stub_update.js",
    "view": "/plugins/docker_challenges/assets/view.js",
}
```

**Important: Python Module Caching**

When you modify the `scripts` dictionary or any Python code:

1. **Changes are cached in memory** by Flask/Werkzeug and won't take effect immediately
2. **You must restart the CTFd container** to reload Python modules:
    ```bash
    docker compose restart ctfd
    ```
3. After restart, **hard refresh your browser** (Ctrl+Shift+R / Cmd+Shift+R) to clear JavaScript cache

**Frontend Architecture - Keep It Simple:**

The challenge view JavaScript (`view.js`) uses a **simple, non-module approach**:

- Single file loaded directly by CTFd's getScript()
- Functions and objects exposed to global scope (e.g., `window.containerStatus`)
- Works reliably with CTFd's AJAX challenge loading
- Compatible with Alpine.js x-data directives

**Why avoid ES6 modules for challenge views:**

- ES6 modules (`type="module"`) load asynchronously
- Alpine.js parses the DOM immediately when challenges load via AJAX
- Race conditions occur when Alpine tries to use components before modules finish loading
- Stub files and complex loading strategies add unnecessary complexity

**Admin forms (create/update) can use ES6 modules:**

- Admin pages load as full page requests (not AJAX)
- Templates have `{% block footer %}` where scripts can inject with `type="module"`
- Shared functionality can be imported from ES6 modules (e.g., `shared/portManagement.js`)

**Testing JavaScript Changes:**

1. **Modify JavaScript file** (e.g., `assets/view.js`)
2. **If you changed Python code** (scripts dict, imports, etc.):
    - Run `docker compose restart ctfd`
    - Wait 5-10 seconds for container to be ready
3. **Hard refresh browser** (Ctrl+Shift+R / Cmd+Shift+R)
4. **Check browser console** for errors
5. **Test functionality** thoroughly before committing

**Browser Cache Notes:**

- Normal refresh (F5) may serve cached JavaScript
- Hard refresh (Ctrl+Shift+R) forces re-download of all assets
- For persistent cache issues, clear browser cache entirely
