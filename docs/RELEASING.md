# Release Guide

Step-by-step guide for publishing a new version of DB Clone Tool.

## Prerequisites

- Git with push access to `master`
- Docker and Docker Hub account (`melihcelenk`)
- GitHub CLI (`gh`) installed (optional, for automated release)

## Release Checklist

### 1. Update Version Numbers

Update version in **all three places**:

```bash
# pyproject.toml
version = "X.Y.Z"

# setup.py
version="X.Y.Z"

# docker-compose.yml
image: db-clone-tool:X.Y.Z
```

### 2. Update CHANGELOG.md

Move `[Unreleased]` items under a new version heading with today's date:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- ...

### Changed
- ...

### Fixed
- ...
```

Add the release link at the bottom:

```markdown
[X.Y.Z]: https://github.com/melihcelenk/db-clone-tool/releases/tag/vX.Y.Z
```

### 3. Update Documentation

- Update version references in `docs/DEPLOYMENT.md` (bottom of file)
- Update Docker image tags in `README.md` if changed

### 4. Commit and Tag

```bash
# Stage all version changes
git add pyproject.toml setup.py docker-compose.yml CHANGELOG.md README.md docs/DEPLOYMENT.md

# Commit
git commit -m "release: vX.Y.Z"

# Create annotated tag
git tag -a vX.Y.Z -m "Release vX.Y.Z - brief description"
```

### 5. Push to GitHub

```bash
git push origin master
git push origin vX.Y.Z
```

### 6. Build and Push Docker Image

```bash
# Build the image
docker build -t melihcelenk/db-clone-tool:X.Y.Z .

# Also tag as latest
docker tag melihcelenk/db-clone-tool:X.Y.Z melihcelenk/db-clone-tool:latest

# Login to Docker Hub (if not already)
docker login

# Push both tags
docker push melihcelenk/db-clone-tool:X.Y.Z
docker push melihcelenk/db-clone-tool:latest
```

### 7. Create GitHub Release

**Option A - GitHub CLI:**

```bash
gh release create vX.Y.Z \
  --title "vX.Y.Z - Brief Title" \
  --notes "## What's New

- Feature 1
- Feature 2

## Docker

\`\`\`bash
docker pull melihcelenk/db-clone-tool:X.Y.Z
\`\`\`

See [CHANGELOG.md](CHANGELOG.md) for full details."
```

**Option B - GitHub Web UI:**

1. Go to https://github.com/melihcelenk/db-clone-tool/releases/new
2. Select tag `vX.Y.Z`
3. Title: `vX.Y.Z - Brief Title`
4. Copy relevant section from CHANGELOG.md into description
5. Click "Publish release"

## Quick Reference

```bash
# Full release flow (example for v0.3.0)
git add pyproject.toml setup.py docker-compose.yml CHANGELOG.md README.md docs/DEPLOYMENT.md
git commit -m "release: v0.3.0"
git tag -a v0.3.0 -m "Release v0.3.0 - new feature description"
git push origin master && git push origin v0.3.0
docker build -t melihcelenk/db-clone-tool:0.3.0 .
docker tag melihcelenk/db-clone-tool:0.3.0 melihcelenk/db-clone-tool:latest
docker push melihcelenk/db-clone-tool:0.3.0
docker push melihcelenk/db-clone-tool:latest
gh release create v0.3.0 --title "v0.3.0 - Feature Name" --generate-notes
```

## Versioning

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Breaking changes (API incompatible)
- **MINOR** (0.X.0): New features (backward compatible)
- **PATCH** (0.0.X): Bug fixes only
