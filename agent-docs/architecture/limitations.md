# Known Limitations and Workarounds

This is a **LIVING DOCUMENT**. Agents working in this codebase should add discoveries here as they encounter issues during implementation.

## Template for Adding Issues

### [Domain] - [Issue Title]

- **Issue**: Brief description of the limitation/bug/quirk
- **Impact**: How it affects development or functionality
- **Workaround**: Solution or mitigation (or "None" if no workaround exists)
- **Reference**: Link to issue, commit, or relevant code

---

## Platform Limitations

### CTFd - Exact Plugin Directory Name Required

- **Issue**: CTFd requires plugin directory to be named exactly `docker_challenges` (underscore, not hyphen)
- **Impact**: Plugin installation fails if directory name doesn't match, breaking plugin discovery
- **Workaround**: Installation instructions specify exact path: `CTFd/CTFd/plugins/docker_challenges`
- **Reference**: `README.md` installation section, CTFd plugin discovery mechanism

### CTFd 2.3.3 - Config JSON List Format

- **Issue**: CTFd 2.3.3's `get_configurable_plugins` function doesn't support list-based `config.json` format
- **Impact**: Admin menu items fail to load in CTFd versions prior to 3.2.1
- **Workaround**: Requires CTFd 3.2.1+ or manual CTFd modification
- **Reference**: https://github.com/CTFd/CTFd/issues/1370, `CLAUDE.md` - "CTFd Integration Notes"

---

## Frontend Development

### Alpine.js - ES6 Module Race Conditions

- **Issue**: CTFd loads challenge views dynamically via AJAX with `getScript()`. ES6 modules (`type="module"`) load asynchronously, creating race conditions when Alpine.js parses the DOM before modules finish loading.
- **Impact**: Alpine.js x-data directives fail to find module-exported functions, breaking reactive components
- **Workaround**: Use global scope functions in `view.js` (expose to `window`). Admin forms can use ES6 modules (full page loads).
- **Reference**: `assets/view.js`, `CLAUDE.md` - "JavaScript/Frontend Development"

### Bootstrap JS API - Not Available as Global

- **Issue**: CTFd does not expose `bootstrap` as a reliable global variable for plugins. The admin theme uses Bootstrap 4 via jQuery compat layer; the core theme uses Bootstrap 5 CSS + Alpine.js. Neither exposes `bootstrap.Modal` for direct use.
- **Impact**: Any code calling `new bootstrap.Modal()` or `bootstrap.Modal.getInstance()` throws `ReferenceError: bootstrap is not defined`
- **Workaround**: Use vanilla JS modal toggling (CSS class manipulation) instead of `bootstrap.Modal` API. Shared helper in `assets/shared/modalUtils.js` exports `showModal()`, `hideModal()`, and `bindDismissButtons()`. Inline scripts in templates define equivalent functions locally (can't import ES modules in inline scripts).
- **Reference**: `assets/shared/modalUtils.js`, `templates/admin_docker_secrets.html`, `templates/admin_docker_status.html`, `assets/view.js`

### CTFd Outer Form - Nested `<form>` Tags Break Submit Handling

- **Issue**: CTFd's admin challenge templates (`admin/challenges/update.html`, `admin/challenges/create.html`) wrap all `{% block %}` content inside a single `<form method="POST">`. HTML forbids nested forms — browsers silently drop the inner `<form>` start tag but the inner `</form>` closes the _outer_ form. This causes any elements after the inner `</form>` (e.g., the Update button) to fall outside the form, breaking CTFd's jQuery submit handler (`$("#challenge-update-container > form").submit()`).
- **Impact**: Challenge update/create buttons silently fail with no error when a nested `<form>` is present in the template
- **Workaround**: Use `<div>` instead of `<form>` for any container inside `{% block category %}` or other template blocks. Use explicit JS validation instead of HTML `required` attributes on inputs inside modals (hidden `required` inputs inside the outer form cause "not focusable" browser validation errors on submit).
- **Reference**: `assets/create_service.html`, `assets/update_service.html`, `assets/shared/secretManagement.js`

### Dynamic Form Loading - DOMContentLoaded Conflicts

- **Issue**: Challenge forms load dynamically via AJAX, not on initial page load. `DOMContentLoaded` event wrappers prevent API calls because DOM already loaded when scripts execute.
- **Impact**: Admin forms fail to populate dropdowns or fetch data from API endpoints
- **Workaround**: Remove DOMContentLoaded wrappers, execute initialization code immediately
- **Reference**: v3.0.0 release notes, `assets/create_*.js`, `assets/update_*.js`

---

## Backend Development

### Python Module Caching - Container Restart Required

- **Issue**: Flask/Werkzeug caches Python modules in memory. Changes to `scripts` dict in `models/*.py` or any Python code don't take effect until container restart.
- **Impact**: JavaScript changes reflected immediately, but Python changes (imports, scripts dict, API logic) require `docker compose restart ctfd`
- **Workaround**: After modifying Python code: (1) `docker compose restart ctfd`, (2) Wait 5-10 seconds, (3) Hard refresh browser (Ctrl+Shift+R)
- **Reference**: `CLAUDE.md` - "JavaScript/Frontend Development - Important: Python Module Caching"

### Docker API - Timeout Failures Block New Launches

- **Issue**: Container cleanup failures (timeouts) prevent new container launches until manual intervention
- **Impact**: Users cannot launch new challenges if previous cleanup failed
- **Workaround**: None currently implemented - requires admin to manually clean up failed containers
- **Reference**: `api/api.py:112` comment, `CLAUDE.md` - "Outstanding Issues"

### Docker Image Metadata - ExposedPorts KeyError

- **Issue**: Some Docker images (e.g., Alpine Linux) don't define ExposedPorts in metadata, causing KeyError when accessing `image_data['Config']['ExposedPorts']`
- **Impact**: Challenge creation crashes when using minimal images
- **Workaround**: Resolved in v3.0.0 with configurable exposed ports feature - admins manually configure ports, `get_required_ports()` handles missing metadata gracefully
- **Reference**: `functions/general.py:get_required_ports()`, `CLAUDE.md` - "Fixed in v3.0.0"

### Docker Tag Aliasing - First Tag Selection

- **Issue**: Plugin reads first tag in `RepoTags` array. Docker images with multiple tags may not display desired tag.
- **Impact**: Admins must ensure desired tag is listed first, or manually alias images before importing
- **Workaround**: Re-tag images to ensure primary tag is first: `docker tag image:secondary image:primary && docker rmi image:secondary`
- **Reference**: `functions/general.py:get_repositories()`, `CLAUDE.md` - "Outstanding Issues"

---

## Development Environment

### Docker Compose - Port Mapping

- **Issue**: CTFd container runs on port 8000 internally, exposed through nginx on port 80
- **Impact**: Direct CTFd access requires connecting to nginx, not CTFd container port
- **Workaround**: Use `http://localhost` (not `http://localhost:8000`) for local development
- **Reference**: `docker-compose.yml`, `CLAUDE.md` - "Running Development Environment"

---

## Testing

### Manual Testing Required - Docker Challenge Validation

- **Issue**: No automated integration tests for Docker container/service creation due to Docker API dependency
- **Impact**: Manual testing checklist required for each Docker challenge type change
- **Workaround**: Follow manual testing checklist in CONTRIBUTING.md before PRs
- **Reference**: `CONTRIBUTING.md` - "Manual Testing" section, `CLAUDE.md` - "Outstanding Issues"

---

## Deployment

### Single Docker Host Architecture

- **Issue**: Plugin designed for single Docker API endpoint, not multi-tenant with multiple hosts
- **Impact**: All challenges run on same Docker host, no load balancing or geographic distribution
- **Workaround**: None - architectural limitation requiring significant redesign for multi-host support
- **Reference**: `models/models.py:DockerConfig` (single row), architecture/decisions.md

### TLS Certificate Permissions

- **Issue**: Docker API TLS certificates must have 0o600 permissions in `/tmp` directory
- **Impact**: Incorrect permissions cause certificate validation failures
- **Workaround**: `do_request()` automatically sets permissions when writing temp files
- **Reference**: `functions/general.py:do_request()`

---

## Future Improvements Needed

### Autocreate Connection Info Based on Service Type

- **Issue**: Connection info (host, port) not automatically populated in challenge description/hints
- **Impact**: Admins must manually format connection strings for players
- **Workaround**: None - feature request
- **Reference**: `CLAUDE.md` - "Outstanding Issues"

### Dynamic Port Pointing

- **Issue**: Port mapping is static at container creation, not updated if containers restart
- **Impact**: Port changes require container recreation
- **Workaround**: None - feature request
- **Reference**: `CLAUDE.md` - "Outstanding Issues"

### Individual Secret Permissions

- **Issue**: Docker secrets have global permission settings (0o600 or 0o777), not per-secret control
- **Impact**: All secrets in a service share same permissions
- **Workaround**: None - feature request
- **Reference**: `CLAUDE.md` - "Outstanding Issues"
