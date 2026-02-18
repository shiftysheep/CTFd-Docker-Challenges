# Build Process Backstory

This document covers ONLY non-standard build aspects. For complete build procedures, see `CONTRIBUTING.md`.

## Build Backstory

**Package Manager**: Uses UV (not pip or Poetry)

- Faster dependency resolution, modern PEP 621 support
- Dependencies in `pyproject.toml`, lockfile in `uv.lock`

**Build Backend**: Hatchling (configuration in `pyproject.toml`)

- Modern PEP 621-compatible build backend
- Version management via Hatchling dynamic metadata

**Code Quality Enforcement**: Pre-commit hooks enforce automatically on every commit

- Ruff (linting + formatting, 100 char line length)
- Xenon (complexity: max B absolute/modules, A average)
- Vulture (dead code detection, 80% confidence)
- Bandit (security scanning)
- Prettier (JavaScript/HTML/CSS/Markdown)
- Commitizen (conventional commits)

**No Build Artifacts**: Plugin deployed as source code (no compilation step)

- Plugin loaded directly by CTFd from `CTFd/CTFd/plugins/docker_challenges/`

## Version Bumping

**Bump the version on the feature branch before merging the PR.** This keeps the bump commit in the same PR and reduces commit noise on `master`. Use Commitizen to auto-detect the increment:

```bash
cz bump --dry-run  # Preview before running
cz bump            # Auto-detects patch/minor/major from commits
```

Commitizen updates `pyproject.toml`, `README.md`, and `CHANGELOG.md`, creates a commit, and tags it.

After merging, retag the squash-merged commit and push the tag:

```bash
git tag -d vX.Y.Z                    # Delete local tag (points to pre-squash commit)
git tag vX.Y.Z <merged-commit-hash>  # Retag on the squash-merged commit
git push origin vX.Y.Z               # Push tag to remote
```
