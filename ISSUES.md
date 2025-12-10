# Known Issues

## 🚫 Blocking Issues (Must Fix Before Merge)

### Build Configuration

- **pyproject.toml - Deprecated license field format**
    - Location: pyproject.toml:7
    - Issue: Using `license = {text = "..."}` format deprecated in setuptools 77.0.0+
    - Impact: Build fails in CI/CD with modern setuptools
    - Fix: Change to `license = "Apache-2.0"`
    - Effort: 5 minutes

- **pyproject.toml - Missing package discovery**
    - Location: pyproject.toml (missing [tool.setuptools] section)
    - Issue: Build error "Multiple top-level packages discovered"
    - Impact: Package installation fails, plugin cannot load
    - Fix: Add `[tool.setuptools]` with `packages = ["docker_challenges"]`
    - Effort: 5 minutes

### Critical Security Issues

- **XSS via unsafe Jinja2 filter in challenge view**
    - Location: docker_challenges/assets/view.html:12
    - Issue: Challenge name rendered with `|safe` filter allows HTML/JavaScript injection
    - Impact: Stored XSS - attackers can steal session cookies, compromise accounts
    - Fix: Remove `|safe` filter (Jinja2 auto-escapes by default)
    - Effort: 2 minutes

- **XSS via x-html directives in admin templates**
    - Location: docker_challenges/templates/admin_docker_status.html:142, 187
    - Issue: Alpine.js `x-html` renders unescaped HTML from backend
    - Impact: XSS in admin context (highest privilege)
    - Fix: Replace `x-html` with `x-text` for safe text rendering
    - Effort: 5 minutes

## ⚠️ High Priority Issues

### Security

- **SSRF vulnerability in image_ports endpoint**
    - Location: docker_challenges/api/api.py:334-371
    - Issue: `image` parameter insufficiently validated before Docker API request
    - Impact: Attackers can specify arbitrary URIs
    - Fix: Add regex validation for Docker image format
    - Effort: 30 minutes

- **CSRF vulnerability - state-changing GET request**
    - Location: docker_challenges/api/api.py:183-204
    - Issue: `/api/v1/nuke` DELETE operation uses GET method
    - Impact: Container deletion via CSRF attack (img src trick)
    - Fix: Change to POST method, update frontend AJAX calls
    - Effort: 1 hour

- **Client-side only port validation**
    - Location: docker_challenges/assets/create.js, update.js, create_service.js, update_service.js
    - Issue: Port validation only enforced in JavaScript (bypassable)
    - Impact: Malicious admin creates invalid challenges → container launch fails
    - Fix: Add server-side validation in DockerChallengeType.create()
    - Effort: 2 hours

### Code Quality

- **Missing type hints - PEP 484 violations**
    - Locations:
        - docker_challenges/api/api.py (13 functions)
        - docker_challenges/functions/general.py (3 functions)
    - Issue: 16 functions missing type annotations
    - Impact: Reduced type safety, poor IDE support, runtime errors undetected
    - Fix: Add type hints to function signatures
    - Effort: 3 hours

- **Assert statements for error handling (SOLID violation)**
    - Location: docker_challenges/api/api.py:43-45
    - Issue: Using `assert` for validation (removed with `python -O`)
    - Impact: Silent failures in production
    - Fix: Replace with explicit error raising
    - Effort: 15 minutes

- **JavaScript error handling - silent failures**
    - Location: All \*.js files in docker_challenges/assets/
    - Issue: Fetch errors only log to console, no user feedback
    - Impact: Confusing UX when API calls fail
    - Fix: Add ezal() alerts for fetch errors
    - Effort: 1 hour

### Code Maintainability

- **Massive code duplication - port management**
    - Locations: create.js, update.js, create_service.js, update_service.js
    - Issue: ~150 lines × 4 files = 600 duplicated lines (60% duplication rate)
    - Impact: Bug fixes require 4× effort, high inconsistency risk
    - Fix: Extract to shared/portManagement.js module
    - Effort: 4 hours

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

- **Magic numbers throughout codebase**
    - Issue: Hardcoded timeouts (7200, 300), port ranges (30000-60000), delays (1000ms)
    - Impact: Difficult to configure, poor maintainability
    - Fix: Extract to constants.py and constants.js
    - Effort: 1 hour

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

- **XMLHttpRequest in modern codebase**
    - Location: admin_docker_status.html:236-254
    - Issue: Old API when rest uses fetch()
    - Fix: Refactor to fetch() with proper error handling
    - Effort: 1 hour

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

- **Unused code - potential cleanup**
    - delete_secret() function (general.py:114) - never called, may be reserved
    - logger import (general.py:9) - imported but unused
    - Impact: Minor code hygiene
    - Effort: 15 minutes

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

**Total Issues**: 25

- **Blocking**: 4 (2 build, 2 critical security)
- **High Priority**: 9 (3 security, 3 code quality, 3 maintainability)
- **Active Bugs**: 2
- **Suggestions/Tech Debt**: 10
- **Feature Requests**: 9

**Estimated Critical Path**: ~10 hours (blocking + high priority security/quality)

**Last Updated**: 2025-12-09 (Code Review via feat/beta-compatibility)
