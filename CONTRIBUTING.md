# Contributing to CTFd Docker Challenges

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to this project.

## Table of Contents

- [Development Environment Setup](#development-environment-setup)
- [Code Quality Standards](#code-quality-standards)
- [Commit Message Conventions](#commit-message-conventions)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Architecture Overview](#architecture-overview)
- [Code Style Guide](#code-style-guide)

## Development Environment Setup

### Prerequisites

- **Python 3.9+** with `pip`
- **Docker** and **Docker Compose**
- **Git** with commit hooks support
- **Node.js 18+** (for Prettier formatting)

### Initial Setup

1. **Clone the repository**

    ```bash
    git clone https://github.com/shiftysheep/CTFd-Docker-Challenges.git
    cd CTFd-Docker-Challenges
    ```

2. **Install Python dependencies**

    ```bash
    pip install flask_wtf
    ```

3. **Install pre-commit hooks**

    ```bash
    # Install pre-commit tool (if not already installed)
    pip install pre-commit

    # Install git hooks
    pre-commit install
    pre-commit install --hook-type commit-msg
    ```

4. **Run pre-commit on all files (optional)**

    ```bash
    pre-commit run --all-files
    ```

### Docker-in-Docker Testing Environment

The repository includes a Docker Compose configuration for testing the plugin in an isolated environment:

```bash
# Start test environment
docker compose up

# CTFd will be available at http://localhost:8000
# Default admin credentials: admin / password

# View logs
docker compose logs -f ctfd

# Restart CTFd after code changes
docker compose restart ctfd

# Clean up
docker compose down
```

**Test Environment Details:**

- **CTFd**: Runs on port 8000 (via container), exposed through nginx on port 80
- **MariaDB**: Database with user/pass: ctfd/ctfd
- **Redis**: Session cache
- **Docker Host**: Accessible from CTFd container for challenge management

## Code Quality Standards

This project uses automated code quality tools enforced via pre-commit hooks.

### Python Code Quality

**Ruff** (replaces Black, isort, and flake8):

- Line length: 100 characters
- Auto-formatting on commit
- Import sorting (isort-compatible)
- Comprehensive linting rules (pycodestyle, pyflakes, bugbear, etc.)

**Xenon** - Code complexity monitoring:

- Maximum absolute complexity: B
- Maximum module complexity: B
- Maximum average complexity: A

**Vulture** - Dead code detection:

- Minimum confidence: 80%
- Scans `docker_challenges/` directory

**Bandit** - Security vulnerability scanning:

- Configured via `pyproject.toml`
- Scans Python files for common security issues

### JavaScript/Frontend Code Quality

**Prettier** - Code formatting:

- Print width: 100 characters
- Single quotes for strings
- Trailing commas (ES5)
- Tab width: 4 spaces

### Running Quality Checks Manually

```bash
# Run all pre-commit hooks
pre-commit run --all-files

# Run specific hook
pre-commit run ruff --all-files
pre-commit run prettier --all-files

# Run Ruff directly
ruff check docker_challenges/
ruff format docker_challenges/

# Run Prettier directly
npx prettier --write "docker_challenges/assets/**/*.{js,html}"
```

## Commit Message Conventions

This project follows [Conventional Commits](https://www.conventionalcommits.org/) specification, enforced by Commitizen.

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, whitespace)
- **refactor**: Code refactoring (no functional changes)
- **perf**: Performance improvements
- **test**: Adding or updating tests
- **build**: Build system or dependency changes
- **ci**: CI/CD configuration changes
- **chore**: Other changes (maintenance, tooling)

### Examples

```bash
# Good commit messages
feat(challenges): add configurable exposed ports with auto-population
fix(api): handle images without ExposedPorts metadata
docs(readme): update installation instructions for CTFd 3.8.0
refactor(containers): simplify port assignment logic
build: setup pre-commit with ruff, xenon, vulture, bandit

# Interactive commit helper
cz commit
```

### Commit Message Validation

The pre-commit `commit-msg` hook validates commit messages automatically. Invalid messages will be rejected:

```bash
# ❌ Will be rejected
git commit -m "updated stuff"

# ✅ Will be accepted
git commit -m "fix(api): resolve port conflict on container creation"
```

## Testing

### Manual Testing Checklist

Before submitting a PR, test the following scenarios:

#### Challenge Creation

- [ ] Create `docker` challenge with image that has exposed ports
- [ ] Create `docker` challenge with image without exposed ports (e.g., Alpine)
- [ ] Create `docker_service` challenge with secrets
- [ ] Verify exposed ports auto-populate from image metadata
- [ ] Verify manual port configuration in Advanced Settings

#### Container Lifecycle

- [ ] Start container from challenge page
- [ ] Verify countdown timer displays correctly (5:00 → 4:59 → ...)
- [ ] Verify connection details show (Host: X.X.X.X Port: XXXXX)
- [ ] Test revert functionality after 5 minutes
- [ ] Verify container cleanup on challenge solve
- [ ] Verify 2-hour stale container cleanup

#### Admin Functions

- [ ] Docker config page saves settings correctly
- [ ] Docker status page shows all active containers
- [ ] Bulk container nuke functionality works
- [ ] Single container termination works

#### Edge Cases

- [ ] Handle multiple users creating containers simultaneously
- [ ] Verify port conflict resolution
- [ ] Test with TLS-enabled Docker API
- [ ] Test with Docker Swarm services

### Running Tests in Docker Environment

```bash
# Execute test script inside container
docker compose exec ctfd python3 /opt/CTFd/test_script.py

# Check logs for errors
docker compose logs ctfd | grep -i error
```

## Pull Request Process

### Before Submitting

1. **Update your branch**

    ```bash
    git checkout master
    git pull origin master
    git checkout your-feature-branch
    git rebase master
    ```

2. **Run quality checks**

    ```bash
    pre-commit run --all-files
    ```

3. **Test your changes**
    - Follow the [Manual Testing Checklist](#manual-testing-checklist)
    - Document any new testing steps

4. **Update documentation**
    - Update `README.md` for user-facing changes
    - Update `CHANGELOG.md` (Unreleased section)
    - Add docstrings to new functions/classes
    - Update `CLAUDE.md` for architecture changes

### Creating the PR

1. **Write a clear PR title** (conventional format)

    ```
    feat(api): add support for custom port mappings
    fix(ui): resolve countdown timer drift after page sleep
    ```

2. **Provide detailed description**

    ```markdown
    ## Summary

    Brief description of changes

    ## Motivation

    Why is this change needed?

    ## Changes

    - Detailed list of changes
    - Include file references

    ## Testing

    - [ ] Manual testing completed
    - [ ] Edge cases verified
    - [ ] Documentation updated

    ## Screenshots

    (If UI changes)
    ```

3. **Link related issues**

    ```
    Fixes #123
    Relates to #456
    ```

### PR Review Process

1. Automated checks must pass (pre-commit hooks on CI)
2. At least one maintainer review required
3. Address review feedback with additional commits
4. Squash or rebase as requested by maintainers
5. Once approved, maintainer will merge

### After Merge

1. Delete your feature branch
2. Pull latest master
3. Release notes will be generated automatically via Commitizen

## Architecture Overview

### Directory Structure

```
docker_challenges/
├── __init__.py           # Plugin initialization, API registration
├── api/
│   ├── __init__.py       # API namespace exports
│   └── api.py            # REST API endpoints
├── assets/               # Frontend JavaScript/HTML
│   ├── create.js         # Challenge creation form
│   ├── update.js         # Challenge update form
│   ├── view.js           # User challenge view
│   └── *.html            # HTML templates
├── functions/            # Core business logic
│   ├── containers.py     # Docker container operations
│   ├── services.py       # Docker Swarm service operations
│   └── general.py        # Docker API communication
├── models/               # Database models and challenge types
│   ├── models.py         # SQLAlchemy models
│   ├── container.py      # Docker challenge type implementation
│   └── service.py        # Service challenge type implementation
└── templates/            # Admin page templates
    ├── docker_config.html
    └── admin_docker_status.html
```

### Key Concepts

#### Challenge Types

Two polymorphic challenge types extend CTFd's base `Challenges` model:

1. **`docker`** (DockerChallenge)
    - Standalone Docker containers
    - Random port assignment (30000-60000)
    - Created via Docker `/containers` API

2. **`docker_service`** (DockerServiceChallenge)
    - Docker Swarm services
    - Supports Docker secrets with configurable permissions
    - Created via Docker `/services` API

#### Container Lifecycle

- **Creation**: User clicks "Start Docker Instance" → API call → Container/Service created
- **Tracking**: `DockerChallengeTracker` model stores instance_id, ports, timestamps
- **Revert**: After 5 minutes, user can delete/recreate container
- **Cleanup**: 2-hour stale containers auto-deleted, or on challenge solve

#### Port Management

- Exposed ports extracted from Docker image metadata (`ExposedPorts`)
- Challenge-specific ports configurable in Advanced Settings
- Random assignment from range 30000-60000, avoiding conflicts
- Port format: `port/protocol` (e.g., `80/tcp`, `443/udp`)

### Adding New Features

#### Example: Adding a New API Endpoint

1. **Create endpoint in `api/api.py`**

    ```python
    @new_namespace.route("", methods=["GET"])
    class NewAPI(Resource):
        @admins_only
        def get(self):
            # Implementation
            return {"success": True, "data": []}
    ```

2. **Export namespace in `api/__init__.py`**

    ```python
    from .api import new_namespace
    ```

3. **Register in `__init__.py`**

    ```python
    CTFd_API_v1.add_namespace(new_namespace, "/new_endpoint")
    ```

4. **Update frontend to consume API**

    ```javascript
    fetch('/api/v1/new_endpoint')
        .then((response) => response.json())
        .then((result) => {
            // Handle result
        });
    ```

## Code Style Guide

### Python

- Follow PEP 8 (enforced by Ruff)
- Type hints preferred for function signatures
- Docstrings for public functions (Google style)
- Avoid bare `except` clauses (use specific exceptions)
- Use context managers for file operations
- Constants in UPPER_CASE

**Example:**

```python
from typing import List, Optional

def get_required_ports(
    docker: DockerConfig,
    image: str,
    challenge_ports: Optional[str] = None
) -> List[str]:
    """
    Get required ports for a challenge, merging image and challenge ports.

    Args:
        docker: Docker configuration object
        image: Docker image name (e.g., "nginx:latest")
        challenge_ports: Comma-separated ports (e.g., "80/tcp,443/tcp")

    Returns:
        List of port strings in Docker format (e.g., ["80/tcp", "443/tcp"])
    """
    ports = set()
    # Implementation...
    return list(ports)
```

### JavaScript

- Use modern ES6+ syntax (const/let, arrow functions, async/await)
- Prefer `fetch()` over jQuery AJAX
- Event listeners over inline onclick handlers
- Template literals for string interpolation
- Descriptive variable names (camelCase)

**Example:**

```javascript
async function fetchDockerImages() {
    try {
        const response = await fetch('/api/v1/docker');
        const result = await response.json();

        if (result.success) {
            populateImageDropdown(result.data);
        }
    } catch (error) {
        console.error('Error fetching Docker images:', error);
    }
}
```

### HTML/Templates

- Bootstrap 5 classes for styling
- Alpine.js for reactive components
- Semantic HTML5 elements
- ARIA attributes for accessibility
- No inline JavaScript (CSP compliant)

### Configuration Files

- YAML: 2-space indentation
- JSON: 4-space indentation (enforced by Prettier)
- TOML: Follow PEP 518 conventions

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/shiftysheep/CTFd-Docker-Challenges/issues)
- **Discussions**: [GitHub Discussions](https://github.com/shiftysheep/CTFd-Docker-Challenges/discussions)
- **Documentation**: See `CLAUDE.md` for detailed architecture notes

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (Apache-2.0).

---

Thank you for contributing! 🎉
