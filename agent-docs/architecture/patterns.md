# Design Patterns and Code Organization

## Primary Architecture: Plugin-Based Extension

**What**: CTFd plugin architecture with polymorphic challenge type system
**Where**: Root `__init__.py` registers plugin, challenge types, blueprints, API namespaces
**Why**: Extends CTFd without core modifications, maintains upgrade compatibility

## Polymorphic Challenge Types

**What**: SQLAlchemy polymorphic inheritance pattern
**Where**: `models/models.py` - `DockerChallenge` and `DockerServiceChallenge` extend CTFd's `Challenges`
**Why**: Seamless integration with CTFd's challenge system (queries, admin forms, scoring)

**Implementation**:

- Both models inherit from CTFd's base `Challenges` model
- Each has unique `polymorphic_identity` ("docker" vs "docker_service")
- Type classes (`DockerChallengeType`, `DockerServiceChallengeType`) implement `BaseChallenge` interface
- CTFd automatically routes operations to correct type implementation

## Challenge Type Interface Pattern

**What**: Each challenge type implements CTFd's `BaseChallenge` interface
**Where**: `models/container.py` and `models/service.py`
**Why**: Standardized lifecycle hooks for creation, updates, flag validation, cleanup

**Required Methods**:

- `create()`: Initialize challenge from admin form data
- `read()`: Serialize challenge data for frontend
- `update()`: Modify existing challenge
- `delete()`: Cleanup challenge and kill all associated containers
- `attempt()`: Validate flag submission
- `solve()`: Record solve and cleanup container (automatic lifecycle)
- `fail()`: Record failed attempt

## Lifecycle Tracking Pattern

**What**: Per-user/team container tracking with automatic cleanup
**Where**: `DockerChallengeTracker` model tracks active instances
**Why**: Prevents resource exhaustion, enforces revert timers, automatic cleanup on solve

**Query Pattern**: Always filter by BOTH `challenge_id` AND `docker_image`

```python
# Correct query pattern
tracker = DockerChallengeTracker.query.filter_by(
    challenge_id=challenge.id,
    docker_image=challenge.docker_image,
    team_id=get_current_team()
).first()
```

**Cleanup Rules**:

- 5-minute revert timer: Enforced in frontend (`view.js` status polling)
- 2-hour stale cleanup: Background job in `api/api.py:110`
- Solve cleanup: Automatic in `solve()` method

## Centralized Docker API Client

**What**: Single function for all Docker API communication
**Where**: `functions/general.py` - `do_request()`
**Why**: Consistent TLS handling, error logging, config management

**Features**:

- HTTP and TLS with client certificate validation
- TLS certs stored as temporary files in `/tmp` (0o600 permissions)
- Centralized error handling and logging
- Config retrieved via `DockerConfig.query.filter_by(id=1).first()`

## Random Port Allocation

**What**: Conflict-free port assignment from 30000-60000 range
**Where**: `functions/containers.py:19-40` and `functions/services.py:18-29`
**Why**: Multi-tenant CTF environment requires dynamic allocation, avoids collisions

**Algorithm**:

1. `get_required_ports()`: Merge image ExposedPorts + challenge-configured ports
2. `get_unavailable_ports()`: Query all active containers/services
3. Random selection from 30000-60000, excluding blocked ports
4. Assign to PortBindings (containers) or PublishedPort (services)

## Container Naming Convention

**What**: Deterministic container names based on image and team
**Where**: `functions/containers.py` and `functions/services.py`
**Why**: Predictable naming for debugging, team isolation

**Format**: `{image}_{md5(team)[:10]}`

- Special characters replaced with underscores
- MD5 hash provides uniqueness without exposing team IDs

## Frontend Script Loading Pattern

**What**: Different JavaScript loading strategies for admin vs player views
**Where**: `scripts` dict in `models/container.py` and `models/service.py`
**Why**: Admin forms load synchronously (full page), player views load via AJAX (race conditions)

**Admin Forms (create/update)**:

- Can use ES6 modules (`type="module"`)
- Load via `{% block footer %}` in templates
- Import shared components (`shared/portManagement.js`, `shared/secretManagement.js`)

**Player View (`view.js`)**:

- Simple, non-module approach (global scope)
- Loaded by CTFd's `getScript()` AJAX mechanism
- Functions exposed to `window` for Alpine.js compatibility
- Avoids ES6 modules to prevent Alpine.js race conditions

## API Namespace Organization

**What**: Functional grouping of REST endpoints
**Where**: Six namespaces registered in `__init__.py`, implemented in `api/api.py`
**Why**: Logical separation, permission control, URL clarity

**Namespaces**:

- `/docker`: Image management (admin)
- `/container`: Container lifecycle (authenticated users)
- `/docker_status`: Status queries (authenticated users)
- `/nuke`: Admin cleanup operations
- `/secret`: Secrets management (admin)
- `/image_ports`: Port metadata queries (admin)

## Configuration Singleton Pattern

**What**: Single-row database config (`DockerConfig.id = 1`)
**Where**: `models/models.py` - `DockerConfig` model
**Why**: Simple, predictable config retrieval without env vars or files

**Retrieval Pattern**: `DockerConfig.query.filter_by(id=1).first()`

## Dynamic Port Configuration

**What**: Challenge-level port overrides with image metadata fallback
**Where**: Frontend (`assets/shared/portManagement.js`), Backend (`functions/general.py:get_required_ports()`)
**Why**: Handles images without ExposedPorts, allows custom port mappings

**Flow**:

1. Admin selects Docker image in challenge form
2. Frontend calls `/api/v1/image_ports` to fetch image metadata
3. Auto-populate port UI with ExposedPorts from image
4. Admin can add/remove ports manually
5. Backend merges challenge ports with image ports at runtime

## Error Handling Pattern

**What**: Consistent error responses with logging
**Where**: `functions/general.py` - `do_request()` checks `response.ok` before `.json()`
**Why**: Docker API errors should log but not crash CTFd

**Implementation**:

- Log Docker API requests at INFO level
- Check `response.ok` before parsing JSON
- Return None on failures, let callers handle gracefully
- API endpoints return HTTP error codes with messages

## Team vs User Mode Pattern

**What**: Conditional queries based on CTFd mode
**Where**: Throughout `api/api.py` and lifecycle functions
**Why**: CTFd supports both individual and team-based CTFs

**Implementation**: `is_teams_mode()` determines whether to use `team_id` or `user_id`
