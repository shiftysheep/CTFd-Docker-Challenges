# Testing Backstory

This document covers ONLY non-standard testing aspects. For complete testing procedures, see `CONTRIBUTING.md`.

## Testing Backstory

**Manual Testing Required**: No automated integration tests for Docker container/service creation

- Docker API dependency makes automated testing complex (requires live Docker daemon)
- Manual testing checklist required for Docker challenge type changes
- See `CONTRIBUTING.md` for manual testing checklist

**Test Framework**: Uses pytest (standard location `tests/`)

- Run with `pytest tests/` (Claude knows pytest flags)
- Configuration in `pyproject.toml`

**Docker Compose for Development**: Development environment provides MariaDB, Redis, nginx for testing

- `docker compose up` starts full stack for manual testing
- CTFd accessible at `http://localhost` (port 80 via nginx)
- Playwright tests against Docker Compose catch format discrepancies (e.g., port string variations) that static code analysis cannot detect—Docker daemon behavior differs from code reading
