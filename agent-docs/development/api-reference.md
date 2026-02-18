# API Reference

Lightweight reference for the Docker Challenges plugin API. All endpoints are under `/api/v1/`.

**Auth levels**:

- **Admin** — requires `@admins_only` (CTFd admin session)
- **Authenticated** — requires `@authed_only` (any logged-in user)

**Request format**: JSON body or form data. **Response format**: JSON with `success` boolean.

---

## Plugin Endpoints

### GET /api/v1/docker

**Auth**: Admin | **Purpose**: List available Docker images for challenge creation forms

**Response** `200`:

```json
{
    "success": true,
    "data": [{ "name": "nginx:alpine" }, { "name": "myregistry:5000/ctf/web:latest" }]
}
```

**Response** `500`:

```json
{ "success": false, "error": "Failed to load Docker images" }
```

> Images are filtered by the repositories configured in `DockerConfig.repositories`.

---

### POST /api/v1/container

**Auth**: Authenticated | **Purpose**: Create a container/service instance for a challenge

**Request body**:

| Field          | Type   | Required | Description              |
| -------------- | ------ | -------- | ------------------------ |
| `id`           | string | yes\*    | Challenge ID             |
| `challenge_id` | string | yes\*    | Challenge ID (alternate) |

\*One of `id` or `challenge_id` must be provided.

**Response** `201`:

```json
{
    "success": true,
    "data": {
        "instance_id": "abc123def456",
        "ports": ["31337/tcp-> 80"],
        "host": "docker.example.com"
    }
}
```

**Response** `403` — container already exists and is under 5 minutes old (revert cooldown):

```json
{ "success": false, "error": "Container creation not allowed" }
```

**Response** `404`:

```json
{ "success": false, "error": "Challenge not found" }
```

**Notable behavior**:

- Cleans up stale containers (>2 hours) for the current user/team before creating
- If an existing container is older than 5 minutes, it is reverted (deleted and recreated)
- Port is randomly assigned from range 30000–60000
- Tracks instance in `DockerChallengeTracker` with `revert_time` timestamp

---

### GET /api/v1/docker_status

**Auth**: Authenticated | **Purpose**: List active container instances for current user/team

**Response** `200`:

```json
{
    "success": true,
    "data": [
        {
            "id": 1,
            "team_id": "5",
            "user_id": null,
            "challenge_id": 42,
            "docker_image": "nginx:alpine",
            "timestamp": 1700000000,
            "revert_time": 1700000300,
            "instance_id": "abc123def456",
            "ports": ["31337/tcp-> 80"],
            "host": "docker.example.com"
        }
    ]
}
```

> In teams mode, filters by `team_id`. In user mode, filters by `user_id`.

---

### POST /api/v1/nuke

**Auth**: Admin | **Purpose**: Kill containers (single or all)

**Request body** — kill single:

```json
{ "container": "abc123def456" }
```

**Request body** — kill all:

```json
{ "all": true }
```

**Response** `200`:

```json
{ "success": true }
```

**Response** `404`:

```json
{ "success": false, "error": "Container not found" }
```

**Notable behavior**:

- `all` accepts boolean `true` or string `"true"` (case-insensitive)
- Kill-all streams in batches of 100 to prevent memory exhaustion

---

### GET /api/v1/secret

**Auth**: Admin | **Purpose**: List Docker secrets

**Response** `200`:

```json
{
    "success": true,
    "data": [{ "name": "db_password", "id": "secret123" }],
    "swarm_mode": true
}
```

> Returns empty `data` array with `swarm_mode: false` when not in swarm mode.

---

### POST /api/v1/secret

**Auth**: Admin | **Purpose**: Create a Docker secret

**Request body**:

| Field  | Type   | Required | Validation                                |
| ------ | ------ | -------- | ----------------------------------------- |
| `name` | string | yes      | `^[a-zA-Z0-9._-]+$`, must be unique       |
| `data` | string | yes      | Secret value (trimmed, must be non-empty) |

**Response** `201`:

```json
{ "success": true, "data": { "id": "secret123", "name": "db_password" } }
```

**Response** `400` — validation or transport error:

```json
{
    "success": false,
    "error": "Secure transport required. Both HTTPS (browser) and Docker TLS must be enabled to transmit secrets safely."
}
```

**Response** `409` — duplicate name:

```json
{ "success": false, "error": "Secret name 'db_password' already in use" }
```

**Notable behavior**:

- Requires both HTTPS (browser) and Docker TLS enabled — rejects otherwise with `400`
- Audit-logs creation with admin username (value is never logged)

---

### DELETE /api/v1/secret/\<secret_id\>

**Auth**: Admin | **Purpose**: Delete a single Docker secret

| Param       | Location | Validation         |
| ----------- | -------- | ------------------ |
| `secret_id` | URL path | `^[a-zA-Z0-9_-]+$` |

**Response** `200`:

```json
{ "success": true, "message": "Secret deleted successfully" }
```

**Response** `409` — secret in use by a service:

```json
{ "success": false, "error": "Cannot delete secret 'db_password' - in use" }
```

**Response** `404`:

```json
{ "success": false, "error": "Secret not found" }
```

---

### DELETE /api/v1/secret/all

**Auth**: Admin | **Purpose**: Bulk-delete all Docker secrets

**Response** `200`:

```json
{
    "success": true,
    "deleted": 3,
    "failed": 1,
    "errors": ["Failed to delete 'active_secret' (likely in use)"]
}
```

> `success` is `false` if any deletion failed. Secrets in use by active services will fail.

---

### GET /api/v1/image_ports

**Auth**: Admin | **Purpose**: Discover exposed ports from a Docker image's metadata

**Query params**:

| Param   | Type   | Required | Validation                                                                |
| ------- | ------ | -------- | ------------------------------------------------------------------------- |
| `image` | string | yes      | Docker image name, max 255 chars, validated against Docker naming pattern |

**Response** `200`:

```json
{ "success": true, "ports": ["80/tcp", "443/tcp"] }
```

**Response** `400`:

```json
{ "success": false, "error": "Invalid Docker image name format" }
```

> Used to auto-populate the `exposed_ports` field in challenge creation forms.

---

## Challenge CRUD via CTFd API

Docker challenges are managed through CTFd's standard challenge API at `/api/v1/challenges`. The plugin registers two polymorphic challenge types that extend the base `Challenges` model with Docker-specific fields.

### Challenge Types

| Type             | `type` value     | Model                    |
| ---------------- | ---------------- | ------------------------ |
| Docker Container | `docker`         | `DockerChallenge`        |
| Docker Service   | `docker_service` | `DockerServiceChallenge` |

### Docker-Specific Fields

**Common fields** (both types):

| Field           | Type   | Description                              |
| --------------- | ------ | ---------------------------------------- |
| `docker_image`  | string | Docker image name (e.g., `nginx:alpine`) |
| `docker_type`   | string | `"container"` or `"service"` (auto-set)  |
| `exposed_ports` | string | Comma-separated ports (e.g., `80/tcp`)   |

**Service-only fields**:

| Field                  | Type   | Description                                                            |
| ---------------------- | ------ | ---------------------------------------------------------------------- |
| `docker_secrets`       | string | JSON array of secret references (stored in DB)                         |
| `docker_secrets_array` | string | JSON array sent in create/update requests (mapped to `docker_secrets`) |

### Read Response

**Container** (`GET /api/v1/challenges/<id>`):

```json
{
    "id": 1,
    "name": "Web Challenge",
    "value": 100,
    "docker_image": "nginx:alpine",
    "exposed_ports": "80/tcp",
    "description": "Find the flag",
    "category": "web",
    "state": "visible",
    "max_attempts": 0,
    "type": "docker",
    "type_data": { "id": "docker", "name": "docker", "templates": {}, "scripts": {} }
}
```

**Service** adds `secrets` (parsed from `docker_secrets`):

```json
{
    "secrets": [{ "name": "db_password", "id": "secret123" }]
}
```

### Create / Update Notes

- `docker_type` is auto-set to `"container"` or `"service"` — do not send manually
- Service challenges: send `docker_secrets_array` (JSON array string) — the plugin maps it to `docker_secrets`
- `exposed_ports` is validated on create and update; invalid format raises `ValueError`

---

## Error Codes

| Code | Meaning      | Common Causes                                    |
| ---- | ------------ | ------------------------------------------------ |
| 400  | Bad request  | Missing params, invalid format, TLS not enabled  |
| 403  | Forbidden    | Container revert cooldown (< 5 min)              |
| 404  | Not found    | Invalid challenge ID, container ID, or secret ID |
| 409  | Conflict     | Duplicate secret name, secret in use             |
| 500  | Server error | Docker API failure, missing Docker config        |
