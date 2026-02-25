# MySQL Schema Clone Tool

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Docker Hub](https://img.shields.io/docker/v/melihcelenk/db-clone-tool?label=Docker%20Hub&logo=docker)](https://hub.docker.com/r/melihcelenk/db-clone-tool)

All-in-one MySQL schema cloning tool. No setup, no CLI — just clone, export, and manage your schemas from the browser.

<img width="2136" height="1343" alt="image" src="https://github.com/user-attachments/assets/e8b883f3-f1bd-436c-b49d-aabc8dee9513" />
<img width="1417" height="892" alt="image" src="https://github.com/user-attachments/assets/1399d4fe-b919-4087-9b61-1ca8a158115a" />


## Features

- **Multiple Connection Management** - Save and manage multiple MySQL database connections
- **Schema Listing** - View all schemas with table counts and size information
- **Schema Cloning** - Duplicate entire schemas with all data and structures
- **Schema Export** - Export schemas as SQL dump files
- **Real-time Progress** - Track cloning progress with live logs and progress bar
- **MySQL Download** - Download and install MySQL binaries directly from the UI
- **Configurable** - Set MySQL bin directory path for mysqldump
- **Cross-platform** - Works on Windows, Linux, and Docker
- **Modern UI** - Clean, responsive web interface
- **RESTful API** - Full API for programmatic access

## Quick Start

### Docker (Recommended)

```bash
docker run -d -p 5000:5000 --name db-clone-tool melihcelenk/db-clone-tool:0.2.0
```

Or build from source:

```bash
git clone https://github.com/melihcelenk/db-clone-tool.git
cd db-clone-tool
docker-compose up -d
```

Open `http://localhost:5000` in your browser. MySQL binaries are pre-installed in the container.

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

### 1. Configure MySQL Bin Path

- Click **"Configure"** in the right panel
- Choose **"Select Installed Version"** or **"Download MySQL"**
- For manual path: enter the path to your MySQL bin directory
  - Windows: `C:/Program Files/mysql-8.0.40-winx64/bin`
  - Linux: `/usr/bin`

> **Note:** Docker users can skip this step - MySQL is pre-configured.

### 2. Add a Database Connection

- Click **"+ Add Connection"** in the left panel
- Fill in: Name, Host, Port, User, Password, Database (optional)
- Click **"Test Connection"** to verify
- Click **"Add Connection"** to save

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
| GET | `/api/config/mysql-bin` | Get MySQL config |
| POST | `/api/config/mysql-bin` | Set MySQL config |
| GET | `/api/mysql/versions` | List MySQL versions |
| POST | `/api/mysql/download` | Download MySQL |
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
│   ├── storage.py           # Connection storage
│   ├── db_manager.py        # Database operations
│   ├── clone_service.py     # Cloning service
│   ├── mysql_download.py    # MySQL download/install
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
- `connections.json` - Saved database connections
- `config.json` - Application settings (MySQL bin path)

## Troubleshooting

| Problem | Solution |
|---------|----------|
| mysqldump not found | Configure MySQL bin path in settings |
| Connection failed | Check host, port, credentials, and firewall |
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
