# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **BREAKING:** Removed hardcoded default MySQL bin paths
- MySQL bin path must now be explicitly configured
- Configuration files moved to `config.local/` directory for better security

### Added
- MySQL download service with version selection
- API endpoint for validating MySQL installation paths (`/api/mysql/validate`)
- API endpoint for fetching available MySQL versions (`/api/mysql/versions`)
- Improved configuration modal with two options: Manual path or Download MySQL
- Path validation button to test MySQL installations
- Comprehensive test coverage for configuration and download services

### Fixed
- Better error handling when MySQL bin path is not configured
- Clear messaging when required executables are missing

## [0.1.0] - 2024-01-XX

### Added
- Initial release
- Web-based MySQL schema cloning tool
- Connection management (add, test, delete connections)
- Schema listing with table count and size information
- Schema cloning using mysqldump
- Real-time progress tracking with logs
- MySQL bin path configuration
- Support for Windows and Linux
- RESTful API endpoints
- Modern web UI with responsive design
- Comprehensive test suite
- Documentation and contribution guidelines

### Features
- Multiple database connection management
- Schema duplication with full data copy
- Background job processing for long-running operations
- Real-time log streaming
- Progress bar visualization
- Context menu for schema operations

[0.1.0]: https://github.com/melihcelenk/db-clone-tool/releases/tag/v0.1.0
