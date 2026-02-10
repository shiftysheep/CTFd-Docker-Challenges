# System Architecture Overview

## Project Purpose

CTFd plugin that extends the CTF platform with Docker-based challenges. Players launch isolated containers/services with automatic lifecycle management (revert timers, stale cleanup, solve cleanup).

## Technology Stack

**Backend**: Python 3.9+ (Flask, SQLAlchemy, CTFd 3.8.0+)
**Frontend**: Alpine.js, Bootstrap 5, vanilla JavaScript
**Infrastructure**: Docker API (HTTP/TLS), Docker Swarm
**Database**: MariaDB (via CTFd)
**Build**: UV package manager, Hatchling build backend
**Quality**: Ruff, Xenon, Vulture, Bandit, Prettier, Commitizen

## High-Level Architecture

```
CTFd Platform
    └── docker_challenges/ (Plugin)
        ├── API Layer (/api/v1/*)
        │   ├── Docker API Client (HTTP/TLS)
        │   └── REST Endpoints (6 namespaces)
        ├── Challenge Types (Polymorphic)
        │   ├── docker (containers)
        │   └── docker_service (swarm services)
        ├── Lifecycle Management
        │   ├── Creation (port allocation)
        │   ├── Tracking (per-user/team)
        │   └── Cleanup (timers + solve)
        └── Admin Interface
            ├── Configuration (Docker API)
            └── Monitoring (active instances)
```

## Directory Structure

```
docker_challenges/
├── __init__.py              # Plugin registration, challenge types, API namespaces
├── config.json              # Admin menu items (Docker config, status)
├── api/
│   └── api.py               # REST API implementations (6 namespaces)
├── models/
│   ├── models.py            # Database models (config, challenges, tracker)
│   ├── container.py         # DockerChallengeType implementation
│   └── service.py           # DockerServiceChallengeType implementation
├── functions/
│   ├── general.py           # Docker API client (HTTP/TLS requests)
│   ├── containers.py        # Container lifecycle (create, ports, cleanup)
│   └── services.py          # Service lifecycle (create, secrets, ports)
├── assets/                  # JavaScript/CSS for admin + challenge views
│   ├── create_*.js/html     # Admin challenge creation forms
│   ├── update_*.js/html     # Admin challenge update forms
│   ├── view.js              # Player challenge view (status polling)
│   └── shared/
│       ├── portManagement.js    # ES6 module for port UI
│       └── secretManagement.js  # ES6 module for secrets UI
└── templates/
    ├── admin_docker_config.html   # Docker API configuration
    ├── admin_docker_status.html   # Monitor active instances
    └── admin_docker_secrets.html  # Docker secrets management
```

## Core Components

### 1. Challenge Type System (Polymorphic)

**docker (Standard Containers)**

- Model: `DockerChallenge` (extends CTFd's `Challenges`)
- Type: `DockerChallengeType` (implements `BaseChallenge`)
- Creates standalone Docker containers via `/containers` API
- Lifecycle: `functions/containers.py`

**docker_service (Swarm Services)**

- Model: `DockerServiceChallenge` (extends CTFd's `Challenges`)
- Type: `DockerServiceChallengeType` (implements `BaseChallenge`)
- Creates Docker swarm services with secrets support
- Lifecycle: `functions/services.py`

Both types implement: `create()`, `read()`, `update()`, `delete()`, `attempt()`, `solve()`, `fail()`

### 2. Lifecycle Management

**Tracking**: `DockerChallengeTracker` model

- Stores: instance_id, ports, host, timestamps, challenge_id, docker_image
- Query pattern: Filter by both `challenge_id` AND `docker_image` (not just ID)

**Automatic Cleanup**:

- 5-minute revert timer: Players can delete/recreate after 5 minutes
- 2-hour stale cleanup: Auto-delete containers older than 2 hours
- Solve cleanup: Container deleted when challenge solved

### 3. Docker API Communication

**Client**: `functions/general.py` - `do_request()`

- Supports HTTP and TLS with client certificate validation
- TLS certs stored as temp files in `/tmp` with 0o600 permissions
- Config: `DockerConfig` model (single row, id=1)

**Operations**:

- `get_repositories()`: List available images (reads first tag in RepoTags array)
- `get_required_ports()`: Merge image ExposedPorts with challenge-configured ports
- `get_unavailable_ports()`: Scan for port conflicts across all instances
- `get_secrets()`: List Docker swarm secrets
- `create_secret()`: Create Docker secret with base64-encoded data
- `delete_secret()`: Delete Docker secret by ID

### 4. Port Allocation Strategy

**Range**: 30000-60000 (production constraint)
**Algorithm**:

1. Merge container's exposed ports (image metadata + challenge configuration)
2. Query all active containers/services for used ports
3. Randomly select from range, excluding blocked ports
4. Assign to container/service PortBindings/PublishedPort

Implementation: `functions/containers.py:19-40`, `functions/services.py:18-29`

### 5. REST API Structure

**Six namespaces** (registered in `__init__.py`):

- `/api/v1/docker`: Fetch available Docker images (admin)
- `/api/v1/container`: Create/revert containers (authenticated users)
- `/api/v1/docker_status`: Get user's active containers
- `/api/v1/nuke`: Admin kill containers (single or all)
- `/api/v1/secret`: Docker secrets CRUD - list (GET), create (POST), delete by ID or bulk (DELETE) (admin)
- `/api/v1/image_ports`: Fetch exposed ports from image metadata (admin)

All implementations: `api/api.py`

### 6. Configurable Exposed Ports Feature

**Added in v3.0.0**: Challenge admins configure exposed ports in Advanced Settings

**Frontend**: Dynamic port management UI (add/remove, TCP/UDP selector)

- Auto-population: Fetches from `/api/v1/image_ports` when image selected
- Multi-hook validation: Ensures at least one port configured

**Backend**:

- Database: `exposed_ports` TEXT column (comma-separated `port/protocol`)
- API: `/api/v1/image_ports` returns image ExposedPorts metadata
- Logic: `get_required_ports()` merges image + challenge ports
- Handles images without ExposedPorts (e.g., Alpine Linux)

### 7. Frontend Architecture

**Admin Forms (create/update)**:

- Use ES6 modules (`type="module"`)
- Load as full page requests (not AJAX)
- Import shared functionality (`shared/portManagement.js`, `shared/secretManagement.js`)

**Challenge View (`view.js`)**:

- Simple, non-module approach (functions in global scope)
- Loaded by CTFd's `getScript()` mechanism
- Alpine.js for reactive status polling
- Avoids ES6 modules to prevent race conditions (see architecture/limitations.md)

## Database Models

**Core Models** (`models/models.py`):

- `DockerConfig`: Single-row config (hostname, TLS settings, repositories)
- `DockerChallenge`: Polymorphic type with `exposed_ports` TEXT column
- `DockerServiceChallenge`: Polymorphic type with secrets + `exposed_ports`
- `DockerChallengeTracker`: Per-user/team active instance tracking

**Polymorphic Integration**: Uses SQLAlchemy polymorphic inheritance from CTFd's base `Challenges` model

## Admin Interface

**Three blueprints** (registered in `__init__.py`):

1. `/admin/docker_config`: Configure Docker API connection, select repositories
2. `/admin/docker_status`: View all active containers across teams/users
3. `/admin/docker_secrets`: Create and manage Docker swarm secrets

Menu items defined in `config.json`

## Technology Choices

**UV over pip/Poetry**: Faster dependency resolution, modern PEP 621 pyproject.toml
**Ruff over Black/flake8/isort**: Single tool for linting and formatting (100 char line length)
**Hatchling over setuptools**: Modern PEP 621-compatible build backend
**Alpine.js over React/Vue**: Lightweight, reactive, CTFd core theme standard
**Random port allocation**: Avoids conflicts in multi-tenant CTF environment
**Polymorphic models**: Seamless integration with CTFd's challenge system
