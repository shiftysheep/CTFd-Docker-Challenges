# Known Issues

## ✅ Fixed in This PR (feat/beta-compatibility)

### Build Configuration

- ✅ **pyproject.toml - Deprecated license field format** - Fixed in `b225341`
    - Changed from `license = {text = "..."}` to `license = "Apache-2.0"`
    - Resolved setuptools 77.0.0+ compatibility issue

- ✅ **pyproject.toml - Missing package discovery** - Fixed in `b225341`
    - Added `[tool.setuptools]` section with `packages = ["docker_challenges"]`
    - Resolved "Multiple top-level packages discovered" build error

### Critical Security Issues

- ✅ **XSS via unsafe Jinja2 filter in challenge view** - Fixed in `d36f0fb`
    - Removed `|safe` filters in docker_challenges/assets/view.html:5
    - Prevents HTML/JavaScript injection through challenge attributes

- ✅ **XSS via x-html directives in admin templates** - Fixed in `d36f0fb`
    - Replaced `x-html` with `x-text` in docker_challenges/templates/admin_docker_status.html:104, 136
    - Eliminates XSS attack vector in admin context

### Code Maintainability

- ✅ **Massive code duplication - port management** - Fixed in `535b179`
    - Created shared/portManagement.js module with 6 exported functions (190 lines)
    - Refactored 4 files: create.js, update.js, create_service.js, update_service.js
    - Eliminated 616 lines of duplicated code (37% reduction)
    - Reduced maintenance burden from 4× to 1× effort

- ✅ **Unused code cleanup** - Fixed in `f45f3d3`
    - Removed delete_secret() function from general.py:120-122 (never called)
    - Removed logger import from general.py:9 (unused variable)
    - Impact: Improved code hygiene, reduced confusion

- ✅ **Magic numbers extraction** - Fixed in `87d85d0`
    - Created constants.py with: CONTAINER_STALE_TIMEOUT_SECONDS (7200), CONTAINER_REVERT_TIMEOUT_SECONDS (300), PORT_ASSIGNMENT_MIN/MAX (30000-60000)
    - Created constants.js with: CONTAINER_POLL_INTERVAL_MS (30000), UI_LOADING_DELAY_MS (1000), MS_PER_SECOND (1000)
    - Updated 7 files to import and use constants: api.py, containers.py, services.py, view.js, portManagement.js
    - Impact: Centralized configuration, improved maintainability

- ✅ **Type hints - PEP 484 compliance** - Fixed in `406a22a`
    - Added type annotations to 16 functions (11 in api.py, 5 in general.py)
    - Imported `typing.Any` for CTFd session types
    - Comprehensive type hints including: DockerConfig, list[int], dict[str, str], tuple types, union types (|), Optional types
    - Impact: Improved type safety, better IDE support, catch errors at development time

### High Priority Security

- ✅ **SSRF vulnerability in image_ports endpoint** - Fixed in `68ddb41`
    - Added regex validation for Docker image format in api.py:347-360
    - Prevents path traversal and URL manipulation attacks
    - Accepts: nginx, nginx:latest, registry.com/user/image:v1.0
    - Rejects: ../../../etc/passwd, http://malicious.com

- ✅ **Assert statements for error handling** - Fixed in `68ddb41`
    - Replaced assert with explicit if/raise RuntimeError pattern in api.py:42-46
    - Prevents silent failures when Python runs with -O optimization

- ✅ **CSRF vulnerability - state-changing GET request** - Fixed in `ce3d463`
    - Changed /api/v1/nuke endpoint from GET to POST method
    - Added CSRF token header (init.csrfNonce) in frontend
    - Replaced XMLHttpRequest with modern fetch() API (bonus improvement)
    - Prevents container deletion via CSRF attack (img src trick)

### User Experience

- ✅ **JavaScript error handling - silent failures** - Fixed in `82acb70`
    - Added ezal() alerts for all fetch errors across 5 JavaScript files (10 total error handlers)
    - create.js: image fetch and image_ports fetch errors
    - update.js: image fetch and image_ports fetch errors
    - create_service.js: image, image_ports, and secrets fetch errors
    - update_service.js: image, image_ports, and secrets fetch errors
    - view.js: persistent status polling errors (conditional to avoid spam)
    - Fixed ES6 module loading: Added `type="module"` to 4 HTML templates
    - Eliminated silent failures, users now receive clear error messages

- ✅ **/api/v1/nuke 500 error - boolean handling** - Fixed in `310b449`
    - Created \_is_truthy() helper to handle both JSON (boolean) and form (string) values
    - Refactored control flow with early returns to reduce complexity (Xenon compliance)
    - Fixed TypeError when frontend sends `true` as boolean vs string "true"

- ✅ **ES6 module loading - multiple issues** - Fixed in `58b04a6`, `e86f1ee`, `8bd8c99`
    - `58b04a6`: Inject scripts via {% block footer %} instead of non-existent {% block scripts %}
    - `e86f1ee`: Use absolute paths (/plugins/.../assets/\*.js) instead of url_for() to avoid KeyError
    - `8bd8c99`: Use window.CTFd to access global from ES6 module scope in 4 JavaScript files
    - Resolved: "CTFd is not defined" ReferenceError
    - Resolved: 500 errors on /challenges and /api/v1/challenges/types
    - Resolved: KeyError: 'view' and KeyError: 'docker_challenges.static'

- ✅ **Server-side port validation** - Fixed in `bfeecf5`
    - Created \_validate_exposed_ports() helper function with comprehensive validation
    - Validates format: port/protocol (e.g., "80/tcp", "443/tcp", "53/udp")
    - Validates port range: 1-65535
    - Validates protocol: tcp or udp only (case-insensitive)
    - Integrated in DockerChallengeType.create() and update() for both challenge types
    - Prevents malicious admin bypass via client-side validation circumvention

- ✅ **ES6 module loading - jQuery getScript() and timing issues** - Fixed in `8f804f2`
    - Problem 1: Empty scripts dict caused jQuery getScript() to load HTML as JavaScript
        - jQuery tried to eval() HTML, causing: "Uncaught SyntaxError: Failed to execute appendChild"
        - Solution: Created 5 stub JavaScript files that satisfy CTFd's getScript() requirement
    - Problem 2: window.CTFd not available when update page modules executed
        - Caused: "Uncaught TypeError: Cannot read properties of undefined (reading 'plugin')"
        - Solution: Added waitForCTFd() polling function in update.js and update_service.js
    - Stub files (minimal console.log only):
        - stub_create.js, stub_update.js, stub_view.js (docker challenges)
        - stub_create_service.js, stub_update_service.js (service challenges)
    - Scripts dict in container.py and service.py now point to stubs
    - Actual ES6 module functionality still loaded via templates with type="module"
    - Resolves final module loading issues, challenge forms now work correctly

## ⚠️ High Priority Issues

### Code Maintainability

- **Excessive function length - docker_config()**
    - Location: docker_challenges/**init**.py:66-138
    - Issue: 73-line function with multiple responsibilities (TLS validation, form processing, repo fetching)
    - Metrics: Complexity ~9, exceeds 50-line guideline
    - Fix: Split into 3 helper functions
    - Effort: 1 hour

- **Excessive function length - create_service()**
    - Location: docker_challenges/functions/services.py:9-62
    - Issue: 54-line function with port assignment and secrets processing tangled
    - Metrics: Complexity ~8, nesting depth 3-4
    - Fix: Extract to \_assign_service_ports() and \_build_secrets_list()
    - Effort: 1 hour

## Active Bugs

- **Race condition in container name collision (timeout failure)**
    - Location: docker_challenges/api/api.py:110-120
    - Issue: Synchronous cleanup blocks requests, inadequate collision handling
    - Impact: Medium - Prevents new container creation after cleanup failure
    - Related: Documented in CLAUDE.md:207
    - Fix (short-term): Optimize cleanup query to filter at database level
    - Fix (long-term): Move cleanup to background Celery task
    - Effort: 1 hour (short-term), 12 hours (long-term)

- **Docker tag aliasing behavior**
    - Location: docker_challenges/functions/general.py (get_repositories)
    - Issue: Plugin reads first tag in image RepoTags array
    - Impact: Images with multiple tags may not appear correctly in repository dropdown
    - Workaround: Remove unwanted tags, leaving only desired tag as primary
    - Effort: TBD (requires Docker API research)

## ℹ️ Suggestions / Technical Debt

- **Unbounded while True loops - port assignment**
    - Locations: containers.py:30-35, services.py:19-29
    - Issue: Infinite loop if all ports occupied
    - Fix: Use bounded iteration with MAX_PORT_ASSIGNMENT_ATTEMPTS
    - Effort: 30 minutes

- **Hardcoded setTimeout delays**
    - Locations: create.js:229, update.js:218, etc.
    - Issue: 1000ms delay assumes button loading time (fragile)
    - Fix: Use MutationObserver to watch for dynamic elements
    - Effort: 30 minutes

- **Inconsistent frontend technology stack**
    - Issue: jQuery + Alpine.js + vanilla JS hybrid across files
    - Impact: Confusing for contributors, larger bundle size
    - Fix: Commit fully to Alpine.js (aligns with CTFd 3.8.0+ core theme)
    - Effort: 6 hours

- **Polling strategy scalability**
    - Location: docker_challenges/assets/view.js:49-50
    - Issue: Linear growth (1000 users = 2000 req/min), no backoff on errors
    - Fix (short-term): Add exponential backoff
    - Fix (long-term): Implement WebSocket/Server-Sent Events
    - Effort: 2 hours (short-term), 16 hours (long-term)

- **Synchronous container cleanup blocking requests**
    - Location: docker_challenges/api/api.py:49-66
    - Issue: Cleanup queries ALL containers, blocks user during sync cleanup
    - Fix (short-term): Optimize query to filter at database level
    - Fix (long-term): Background Celery task
    - Effort: 1 hour (short-term), 12 hours (long-term)

## Feature Requests

- Create secrets from CTFd into docker
- Autocreate connection info based on service type
- Dynamic port pointing (avoid hardcoded port ranges)
- Individual secret permissions (per-secret permission control)
- Mark flags as secret (autocreate secrets from flag values)
- WebSocket real-time updates (replace polling)
- TypeScript migration for type safety
- Database indexes for performance (team_id+challenge_id, timestamp)

## Fixed in v3.0.0

- ✅ **Dynamic form loading** - Removed DOMContentLoaded wrappers preventing API calls in challenge creation forms
- ✅ **Bootstrap tooltip initialization** - Removed code attempting to use undefined `bootstrap` global
- ✅ **ExposedPorts KeyError** - Resolved with configurable exposed ports feature:
    - Added exposed_ports TEXT column to challenge models
    - Created /api/v1/image_ports endpoint for metadata fetching
    - Enhanced get_required_ports() to merge image + challenge ports
    - Gracefully handles images without ExposedPorts (e.g., Alpine Linux)
- ✅ **Frontend migration to Alpine.js and Bootstrap 5** - Modernized challenge view with reactive components
- ✅ **API refactoring** - Extracted helper functions for maintainability (\_cleanup_stale_containers, \_get_existing_container, etc.)

---

## Summary Statistics

**Total Issues**: 14 (15 fixed in this PR)

- **Fixed in This PR**: 15 (4 blocking + 4 high-priority security + 1 maintainability + 3 UX/bug fixes + 3 code quality)
- **Blocking**: 0 ✅
- **High Priority**: 2 (2 maintainability refactoring tasks)
- **Active Bugs**: 2
- **Suggestions/Tech Debt**: 7
- **Feature Requests**: 9

**Estimated Critical Path**: ~2 hours (remaining high priority maintainability)

**Last Updated**: 2025-12-09 (Updated after type hints addition)
