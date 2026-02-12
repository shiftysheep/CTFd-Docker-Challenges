# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

### Added

- Initial release of CTFd Docker Challenges plugin
- Support for Docker container and Docker Swarm service challenges
- Automatic container lifecycle management with revert timers
- Docker secrets support for service challenges
- Admin interface for Docker configuration and status monitoring
- Port assignment system with conflict avoidance (ports 30000-60000)
- 2-hour auto-cleanup for stale containers
- Container deletion on challenge solve

[unreleased]: https://github.com/shiftysheep/CTFd-Docker-Challenges/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/shiftysheep/CTFd-Docker-Challenges/releases/tag/v1.0.0

## v3.1.0 (2026-02-12)

### Feat

- **secrets**: add Docker secrets CRUD management and container POST API

### Fix

- harden secret request validation and modal submit reset
- **security**: address pre-merge review findings
- **api**: return 404 instead of 403 for challenge not found
- **security**: change do_request to return None on failure and guard all callers
- **security**: remove XSS-vulnerable safe filters from admin_docker_status.html
- **security**: add encodeURIComponent to secret DELETE URL
- **logging**: convert f-string logging to lazy evaluation
- **security**: add secret_id regex validation in DELETE endpoint
- **secrets**: return success:false on bulk delete partial failure
- **security**: add usedforsecurity=False to MD5 hash calls
- **secrets**: require both HTTPS and Docker TLS for secret transmission
- **tracker**: add challenge_id filter and document lazy import rationale

### Refactor

- add waitForCTFd timeout and extract shared port-finding logic
- add TYPE_CHECKING guards, test infrastructure, and model updates

## v3.0.0 (2025-12-10)

### Feat

- **polling**: implement exponential backoff for container status polling
- add comprehensive type hints (PEP 484 compliance)
- **security**: add server-side port validation to prevent bypass
- **ux**: add comprehensive JavaScript error handling with user-facing alerts
- **challenges**: add configurable exposed ports with auto-population

### Fix

- **lint**: resolve all ruff linting errors
- **security**: resolve code review findings and eliminate high-priority issues
- **ports**: prevent infinite loops in port assignment
- **ui**: resolve Alpine.js race condition in challenge view loading
- **view**: load view.js module at top of description block
- **view**: add missing ES6 module script tags to view.html template
- **view**: expose containerStatus to global scope for Alpine.js
- **view**: add required CTFd challenge interface to stub_view.js
- **cleanup**: optimize database query for stale container cleanup
- **ui**: resolve ES6 module loading and CTFd timing issues
- **modules**: empty scripts dict to prevent dynamic ES6 execution
- **ui**: use window.CTFd to access global from ES6 modules
- **templates**: use absolute paths instead of url_for for static assets
- **modules**: inject module scripts via footer block for proper loading
- **modules**: remove scripts dict to allow template control of module loading
- **api**: handle boolean values in /api/v1/nuke POST endpoint
- **security**: resolve CSRF vulnerability in container deletion endpoint
- **security**: replace assert statements and add SSRF protection
- **security**: patch critical XSS vulnerabilities in templates
- **build**: update pyproject.toml for setuptools compatibility
- **ui**: initialize Alpine.js stores immediately to prevent undefined errors
- **ui**: add fallback for Bootstrap Modal API when not available

### Refactor

- **functions**: add type hints and fix import organization
- **code-quality**: complete final tech debt items from code review
- **code-quality**: eliminate technical debt from code review
- **ui**: replace setTimeout with MutationObserver for button detection
- extract magic numbers to constants
- **services**: extract port assignment and secrets building logic
- **admin**: extract docker_config helpers and fix secrets API errors
- **ui**: extract port management to shared module
- **ui**: migrate modals to Alpine.js store pattern
- **ui**: remove console error from Bootstrap fallback
