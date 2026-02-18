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

## Playwright Testing (Browser Automation)

**Purpose**: Catch runtime discrepancies that static analysis misses (e.g., Docker API port format variations, UI rendering issues). The copyable connection URLs feature exposed a port format bug only visible when running against a live Docker daemon.

**Prerequisites**: Docker Compose environment running (`docker compose -f docker-compose.test.yml up`)

**Artifact Directory**: All screenshots and test outputs go in `test-artifacts/` (gitignored). Configure Playwright MCP screenshot filenames to use this directory (e.g., `test-artifacts/challenge-view.png`).

### Testing Workflow

1. Start Docker Compose environment (`docker compose -f docker-compose.test.yml up`)
2. Run Playwright tests — navigate, interact, take screenshots to `test-artifacts/`
3. Use descriptive screenshot filenames (e.g., `test-artifacts/challenge-ports-verified.png`)
4. Check browser console for errors (`browser_console_messages`)
5. Restart CTFd if Python changes were made (`docker compose restart ctfd` + hard browser refresh)

### Cleanup Requirements

After every Playwright session, before committing:

1. Remove `test-artifacts/` contents: `rm -rf test-artifacts/*`
2. Remove Playwright MCP state: `rm -rf .playwright-mcp/`
3. Verify clean working tree: `git status` should show no untracked `.png`, `.jpeg`, or `.playwright-mcp/` files

**Why this matters**: Screenshot files and `.playwright-mcp/` directories left behind will show as untracked files and risk accidental commits.
