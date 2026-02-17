# CTFd Docker Plugin

This plugin for CTFd allows competing teams/users to start dockerized images for presented challenges. It adds a challenge type "docker" that can be assigned a specific docker image/tag.

> **For Contributors**: See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code quality standards, and contribution guidelines.

## Version 3.1.2

**Latest Update**: Migrated to Alpine.js and Bootstrap 5 for CTFd 3.8.0+ (core theme)

### Requirements

- **CTFd 3.8.0+** (includes core theme with Alpine.js and Bootstrap 5)
- **Python 3.x** with `flask_wtf` installed (`pip install flask_wtf`)
- **Docker API** accessible via HTTP or TLS
- **Modern Browser**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+ (IE11 not supported)

### Key Features

- Allows players to create their own docker container for docker challenges
- Configurable exposed ports with auto-population from Docker images
- 5 minute revert timer with self-correcting countdown
- 2 hour stale container auto-cleanup
- Status panel for Admins to manage active containers
- Support for TLS docker API connections with client certificate validation (HIGHLY RECOMMENDED)
- Docker container auto-cleanup on solve
- Seamless integration with CTFd core theme
- Content Security Policy (CSP) compliant - no inline JavaScript

### Configuration Requirements

- Docker Config must be set first via `/admin/docker_config`
- Currently supported: plain HTTP (no encryption) or full TLS with client certificate validation
- TLS configuration guide: https://docs.docker.com/engine/security/https/
- Challenges stored by repository tags (e.g., `stormctf/infosecon2019:arbit`)

## Migration from v2.x

**Migration summary:**

- v3.0.0 requires CTFd 3.8.0+ (core theme)
- No database changes - existing challenges work without modification
- Frontend modernized with Alpine.js + Bootstrap 5
- All features maintain functional parity with v2.x
- Known fixes: Dynamic form loading, ExposedPorts handling for images without ports

## Important Notes

- Using the same Docker tag for multiple challenges may cause issues - not fully tested
- Security test your installation before production use
- ~~CTFd 2.3.3 required `get_configurable_plugins` modification~~ (Fixed in CTFd 3.2.1+)
- Active containers continue running during plugin upgrades/downgrades

## Installation / Configuration

### Quick Start

1. **Install CTFd 3.8.0+**

    ```bash
    cd CTFd
    git checkout 3.8.0  # or later
    ```

2. **Install Plugin**

    ```bash
    # Clone into plugins directory
    git clone https://github.com/shiftysheep/CTFd-Docker-Challenges.git CTFd/CTFd/plugins/docker_challenges

    # Install Python dependencies
    pip install flask_wtf
    ```

3. **Restart CTFd**

    ```bash
    # Docker Compose
    docker-compose restart ctfd

    # Or manual restart
    python3 serve.py
    ```

4. **Configure Docker API**
    - Navigate to `/admin/docker_config`
    - Add Docker API connection details (hostname:port)
    - Enable TLS if using secure connection (recommended)
    - Select repositories containing challenge images
    - Click Submit

5. **Create Docker Challenges**
    - Go to Challenges → Create Challenge
    - Select `docker` or `docker_service` as challenge type
    - Choose Docker image from dropdown (sorted alphabetically)
    - Configure challenge as normal (name, description, flags, etc.)
    - Click Submit

6. **Verify Functionality**
    - View challenge as user
    - Click "Start Docker Instance"
    - Verify countdown timer displays (5:00 → 4:59 → ...)
    - Verify connection details show (Host: X.X.X.X Port: XXXXX)
    - Test revert functionality after timer expires

## Contributing

Interested in contributing? See [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Development environment setup
- Code quality standards and pre-commit hooks
- Commit message conventions
- Testing guidelines
- Pull request process

## Release History

See [CHANGELOG.md](CHANGELOG.md) for detailed version history and release notes.

## Credits

- https://github.com/offsecginger (Twitter: @offsec_ginger)
- Jaime Geiger (For Original Plugin assistance) (Twitter: @jgeigerm)
