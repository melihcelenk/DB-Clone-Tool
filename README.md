# MySQL & PostgreSQL Schema Clone Tool

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Docker Hub](https://img.shields.io/docker/v/melihcelenk/db-clone-tool?label=Docker%20Hub&logo=docker)](https://hub.docker.com/r/melihcelenk/db-clone-tool)

All-in-one schema cloning tool for **MySQL** and **PostgreSQL**. No setup, no CLI — just clone, export, and manage your schemas from the browser.

<img width="2136" height="1343" alt="image" src="https://github.com/user-attachments/assets/e8b883f3-f1bd-436c-b49d-aabc8dee9513" />
<img width="1417" height="892" alt="image" src="https://github.com/user-attachments/assets/1399d4fe-b919-4087-9b61-1ca8a158115a" />


## Features

- **Dual Engine** - MySQL and PostgreSQL, selectable per connection
- **Multiple Connection Management** - Save and manage many database connections
- **Schema Listing** - View all schemas with table counts and size information
- **Schema Cloning** - Duplicate entire schemas with tables, data, triggers, procedures, and events (mysqldump/mysql for MySQL, pg_dump/pg_restore for PostgreSQL)
- **Schema Export** - Export schemas as SQL dump / PostgreSQL custom-format files
- **Real-time Progress** - Track cloning progress with live logs and progress bar
- **Binaries Built-in** - MySQL 8.0.40 and PostgreSQL 16.6 pre-installed in the Docker image; additional PG versions (13–17) downloadable from the UI
- **Configurable** - Set MySQL / PostgreSQL bin directory paths from the UI
- **Cross-platform** - Works on Windows, Linux, and Docker
- **Modern UI** - Clean, responsive web interface
- **RESTful API** - Full API for programmatic access

## Quick Start

### Docker (Recommended)

```bash
docker run -d -p 5000:5000 --name db-clone-tool melihcelenk/db-clone-tool:latest
```

Or build from source:

```bash
git clone https://github.com/melihcelenk/db-clone-tool.git
cd db-clone-tool
docker-compose up -d
```

Open `http://localhost:5000` in your browser. MySQL 8.0.40 and PostgreSQL 16.6 client binaries are pre-installed in the container.

> Use a specific version for reproducible deployments: `melihcelenk/db-clone-tool:0.3.1`

### Windows

Double-click `run.bat` - packages install automatically on first run.

### Linux / macOS

```bash
./run.sh
```

Virtual environment and dependencies are set up automatically.

## Installation

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed deployment instructions including Docker Compose configuration, native installation, and environment variables.

### Manual Installation

```bash
git clone https://github.com/melihcelenk/db-clone-tool.git
cd db-clone-tool
pip install -r requirements.txt
python -m src.db_clone_tool.main
```

## Usage

### 1. Configure Bin Paths (MySQL / PostgreSQL)

- Click **"Configure"** next to the relevant engine in the right panel
- Choose **"Select Installed Version"** or **"Download"** a supported release
- For manual path, enter the bin directory containing the client tools:
  - MySQL — `mysqldump`, `mysql` (e.g. `C:/Program Files/mysql-8.0.40-winx64/bin`, `/usr/bin`)
  - PostgreSQL — `pg_dump`, `pg_restore`, `psql` (e.g. `C:/Program Files/PostgreSQL/16/bin`, `/usr/lib/postgresql/16/bin`)

> **Note:** Docker users can skip this step — MySQL 8.0.40 and PostgreSQL 16.6 are pre-configured.

### 2. Add a Database Connection

- Click **"+ Add Connection"** in the left panel
- Choose engine (MySQL / PostgreSQL), then fill in: Name, Host, Port, User, Password, Database (optional)
- Click **"Test Connection"** to verify
- Click **"Add Connection"** to save
- Running the tool in Docker and connecting to a DB on your host? Just type `localhost` — the tool transparently rewrites loopback addresses to `host.docker.internal` so it "just works".

### 3. View and Clone Schemas

- Click on a connection to view its schemas
- Right-click on a schema for options:
  - **Duplicate** - Clone the schema to a new name
  - **Export** - Export schema as SQL dump
- Monitor progress in real-time

### Command Line (API)

```bash
# List connections
curl http://localhost:5000/api/connections

# Add connection
curl -X POST http://localhost:5000/api/connections \
  -H "Content-Type: application/json" \
  -d '{"name": "My DB", "host": "localhost", "port": 3306, "user": "root", "password": "pass"}'

# List schemas
curl http://localhost:5000/api/schemas/{connection_id}

# Clone schema
curl -X POST http://localhost:5000/api/clone \
  -H "Content-Type: application/json" \
  -d '{"connection_id": "uuid", "source_schema": "original", "target_schema": "backup"}'
```

## API Documentation

See [docs/API.md](docs/API.md) for full API reference.

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/connections` | List all connections |
| POST | `/api/connections` | Add a connection |
| POST | `/api/connections/test` | Test a connection |
| DELETE | `/api/connections/{id}` | Delete a connection |
| GET | `/api/schemas/{id}` | List schemas |
| POST | `/api/clone` | Start clone job |
| GET | `/api/clone/status/{id}` | Get clone status |
| GET | `/api/clone/logs/{id}` | Get clone logs |
| GET | `/api/config/mysql-bin` | Get MySQL config (path + version) |
| POST | `/api/config/mysql-bin` | Set MySQL config |
| GET | `/api/config/postgres-bin` | Get PostgreSQL config (path + version) |
| POST | `/api/config/postgres-bin` | Set PostgreSQL config |
| GET | `/api/mysql/versions` | List MySQL versions |
| POST | `/api/mysql/download` | Download MySQL |
| GET | `/api/postgres/versions` | List PostgreSQL versions |
| POST | `/api/postgres/download` | Download PostgreSQL |
| GET | `/api/health` | Health check |

## Docker Usage

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# View logs
docker-compose logs -f

# Rebuild
docker-compose build --no-cache && docker-compose up -d
```

**Persistent Data** (via volume mounts):
- Connections: `./config.local`
- Exports: `./tmp`

## Project Structure

```
db-clone-tool/
├── src/db_clone_tool/
│   ├── main.py              # Application entry point
│   ├── config.py            # Configuration management
│   ├── network.py           # Docker-aware host resolution
│   ├── storage.py           # Connection storage
│   ├── db_manager.py        # MySQL operations
│   ├── postgres_manager.py  # PostgreSQL operations
│   ├── db_manager_factory.py # Engine selection per connection
│   ├── clone_service.py     # Cloning service (both engines)
│   ├── mysql_download.py    # MySQL download/install
│   ├── postgres_download.py # PostgreSQL download/install
│   ├── routes/              # Flask blueprints
│   ├── templates/           # HTML templates
│   └── static/              # CSS, JS
├── tests/                   # Test suite
├── docs/                    # Documentation
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Development

```bash
# Install dev dependencies
pip install -r requirements.txt -r requirements-dev.txt
pip install -e .

# Run tests
pytest

# Run with coverage
pytest --cov=src.db_clone_tool --cov-report=html
```

## Configuration

Config files are stored in `config.local/` (gitignored):
- `connections.json` - Saved database connections (MySQL and PostgreSQL)
- `config.json` - Application settings (MySQL and PostgreSQL bin paths)

## Troubleshooting

| Problem | Solution |
|---------|----------|
| mysqldump / pg_dump not found | Configure the corresponding bin path in settings |
| Connection failed | Check host, port, credentials, and firewall |
| Connection failed to host DB from Docker | Use `localhost` — the tool rewrites it to `host.docker.internal` automatically; on Linux Docker ensure `--add-host host.docker.internal:host-gateway` is set |
| Clone fails | Verify CREATE DATABASE permission and disk space |
| Port 5000 in use | Change port in `docker-compose.yml`: `"8080:5000"` |

## Security

- Passwords are base64 encoded before storage (basic obfuscation)
- For production use, consider implementing stronger encryption
- Never commit `config.local/` to version control
- See [SECURITY.md](SECURITY.md) for security policy

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

**Melih Celenk** - [@melihcelenk](https://github.com/melihcelenk)

## Support

- [Report a Bug](https://github.com/melihcelenk/db-clone-tool/issues)
- [Request a Feature](https://github.com/melihcelenk/db-clone-tool/issues)
