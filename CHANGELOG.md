# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-02-25

### Added
- **Docker support** with multi-stage build and docker-compose
  - Pre-installed MySQL binaries from official MySQL 8.0.40 image
  - Non-root container execution for security
  - Health checks and automatic restart
  - Volume persistence for configurations and exports
- **MySQL download service** with version selection
  - API endpoint for fetching available MySQL versions (`/api/mysql/versions`)
  - API endpoint for validating MySQL installation paths (`/api/mysql/validate`)
  - Installed version detection and status display
  - Repair and re-download support
- **Schema selection enhancements**
  - Multi-schema selection with bulk operations
  - Export modal for SQL dump downloads
  - Active connection button state management
- **Custom notification system** replacing browser alert/confirm dialogs
- **Cross-platform support** with platform-specific startup scripts
  - `run.sh` for Linux/macOS with auto-venv setup
  - `run.bat` for Windows with one-click launch
  - `run.py` for cross-platform Python launcher
- **Comprehensive documentation**
  - API reference (`docs/API.md`)
  - Deployment guide (`DEPLOYMENT.md`)
  - Quick start guide (`QUICKSTART.md`)
  - Contributing guidelines (`CONTRIBUTING.md`)
  - Security policy (`SECURITY.md`)

### Changed
- **BREAKING:** Removed hardcoded default MySQL bin paths
- MySQL bin path must now be explicitly configured or downloaded via UI
- Configuration files moved to `config.local/` directory for better security
- Improved configuration modal with manual path and download options

### Fixed
- MySQL binary path resolution across different platforms
- Better error handling when MySQL bin path is not configured
- Clear messaging when required executables are missing

### Core (from initial development)
- Web-based MySQL schema cloning tool
- Connection management (add, test, delete connections)
- Schema listing with table count and size information
- Schema cloning using mysqldump
- Real-time progress tracking with logs
- Multiple database connection management
- Schema duplication with full data copy
- Background job processing for long-running operations
- Real-time log streaming and progress bar visualization
- Context menu for schema operations
- RESTful API endpoints
- Modern web UI with responsive design
- Comprehensive test suite

[0.2.0]: https://github.com/melihcelenk/db-clone-tool/releases/tag/v0.2.0
