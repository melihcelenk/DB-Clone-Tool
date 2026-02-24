# MySQL Schema Clone Tool

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Docker Hub](https://img.shields.io/docker/v/melihcelenk/db-clone-tool?label=Docker%20Hub&logo=docker)](https://hub.docker.com/r/melihcelenk/db-clone-tool)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Web-based MySQL database schema cloning tool using `mysqldump`. Clone entire database schemas with all tables, data, triggers, procedures, and events through an intuitive web interface.

## 🚀 Quick Start

### Docker (Recommended)

**Pull from Docker Hub and run:**

```bash
docker run -d -p 5000:5000 --name db-clone-tool melihcelenk/db-clone-tool:0.2.0
```

**Or with docker-compose (from source):**

```bash
git clone https://github.com/melihcelenk/db-clone-tool.git
cd db-clone-tool
docker-compose up -d
```

- MySQL binaries pre-installed in container
- Configurations persisted via volumes
- Automatic restart on failure
- Access at `http://localhost:5000`

**Stop the service:**
```bash
docker-compose down
```

### Windows

**One-click run:**

1. **Double-click** on `run.bat`
2. Packages will be installed automatically on first run
3. Browser will open automatically

### Linux / macOS

**One-command run:**

```bash
./run.sh
```

**First-time setup:**
- Script will auto-create virtual environment
- Dependencies will be auto-installed
- Application starts at `http://localhost:5000`

For detailed usage see [QUICKSTART.md](QUICKSTART.md).

## Features

- 🗄️ **Multiple Connection Management** - Save and manage multiple MySQL database connections
- 📋 **Schema Listing** - View all schemas with table counts and size information
- 🔄 **Schema Cloning** - Duplicate entire schemas with all data and structures
- 📊 **Real-time Progress** - Track cloning progress with live logs and progress bar
- ⚙️ **Configurable** - Set MySQL bin directory path for mysqldump
- 🖥️ **Cross-platform** - Works on Windows and Linux
- 🎨 **Modern UI** - Clean, responsive web interface
- 🔌 **RESTful API** - Full API for programmatic access

## Screenshots

*Add screenshots here*

## Installation

### Docker Deployment (Recommended)

**Requirements:**
- Docker 20.10+
- Docker Compose 1.29+

**Option A - Pull from Docker Hub (fastest):**

```bash
docker run -d \
  -p 5000:5000 \
  -v ./config.local:/app/config.local \
  -v ./tmp:/app/tmp \
  --name db-clone-tool \
  --restart unless-stopped \
  melihcelenk/db-clone-tool:0.2.0
```

**Option B - Build from source:**

```bash
# Clone repository
git clone https://github.com/melihcelenk/db-clone-tool.git
cd db-clone-tool

# Start with Docker Compose
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

**Access:**
- Web UI: `http://localhost:5000`
- Health check: `http://localhost:5000/api/health`

**MySQL binaries are pre-installed** in the Docker image at `/app/mysql/bin`.

### Native Installation

**Requirements:**
- Python 3.8 or higher
- MySQL server with `mysqldump` and `mysql` binaries (or use download feature)
- pip (Python package manager)

### Quick Start

#### Windows

**Easiest method - Double-click to run:**

1. Download or clone the project
2. Double-click on `run.bat`
   - Necessary packages will be installed automatically on first run
   - Browser will open automatically
   - Application will run at `http://localhost:5000`

#### Linux / macOS

**Easiest method - One-command run:**

1. Download or clone the project
2. Run in terminal:
   ```bash
   ./run.sh
   ```
   - Virtual environment created automatically
   - Packages installed automatically on first run
   - Application will run at `http://localhost:5000`

**Note:** On first run, make sure `run.sh` is executable:
```bash
chmod +x run.sh
```

### Manual Installation

1. Clone the repository:

```bash
git clone https://github.com/melihcelenk/db-clone-tool.git
cd db-clone-tool
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the application:

```bash
python -m src.db_clone_tool.main
```

Or install as a package:

```bash
pip install -e .
db-clone-tool
```

4. Open your browser and navigate to:

```
http://localhost:5000
```

### Linux/macOS

**Easiest method - One-command run:**

```bash
./run.sh
```

- Virtual environment will be created automatically
- Dependencies will be installed automatically
- Application starts at `http://localhost:5000`

**Alternative methods:**

```bash
# Using Python directly
python3 -m src.db_clone_tool.main

# Or with manual venv setup
python3 -m venv venv
source venv/bin/activate
pip install -e .
python -m src.db_clone_tool.main
```

## Usage

### Startup (Windows)

**Easiest method - One-click run:**

- **Double-click** on `run.bat`
- Packages will be installed automatically on first run
- Browser will open automatically (`http://localhost:5000`)

**Note:** Python packages will be installed automatically on first run. Internet connection is required.

For detailed usage see [QUICKSTART.md](QUICKSTART.md).

### Quick Start

1. **Configure MySQL Bin Path**

   - Click "Configure" in the right panel
   - Enter the path to your MySQL bin directory
   - Example (Windows): `C:/Program Files/mysql-5.7.44-winx64/bin`
   - Example (Linux): `/usr/bin`
2. **Add a Database Connection**

   - Click "+ Add Connection" in the left panel
   - Fill in connection details:
     - Name: A friendly name for the connection
     - Host: MySQL server hostname or IP
     - Port: MySQL server port (default: 3306)
     - User: MySQL username
     - Password: MySQL password
     - Database: (Optional) Specific database to connect to
   - Click "Test Connection" to verify
   - Click "Add Connection" to save
3. **View Schemas**

   - Click on a connection in the left panel
   - All schemas will be listed in the middle panel
   - Each schema shows:
     - Number of tables
     - Total size in MB
4. **Clone a Schema**

   - Right-click on a schema
   - Select "Duplicate"
   - Enter the target schema name (e.g., `backup_6f`)
   - Click "Start Clone"
   - Monitor progress in real-time
   - The new schema will appear in the list when complete

### Command Line

You can also use the tool programmatically via the REST API:

```bash
# List connections
curl http://localhost:5000/api/connections

# Add connection
curl -X POST http://localhost:5000/api/connections \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production DB",
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "password",
    "database": "mydb"
  }'

# List schemas
curl http://localhost:5000/api/schemas/{connection_id}

# Clone schema
curl -X POST http://localhost:5000/api/clone \
  -H "Content-Type: application/json" \
  -d '{
    "connection_id": "{connection_id}",
    "source_schema": "original_schema",
    "target_schema": "backup_schema"
  }'
```

## API Documentation

### Connections API

#### GET `/api/connections`

Get all saved connections.

**Response:**

```json
[
  {
    "id": "uuid",
    "name": "Connection Name",
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "database": "mydb"
  }
]
```

#### POST `/api/connections`

Add a new connection.

**Request Body:**

```json
{
  "name": "Connection Name",
  "host": "localhost",
  "port": 3306,
  "user": "root",
  "password": "password",
  "database": "mydb"
}
```

**Response:**

```json
{
  "success": true,
  "connection_id": "uuid"
}
```

#### POST `/api/connections/test`

Test a connection without saving.

**Request Body:** Same as POST `/api/connections`

**Response:**

```json
{
  "success": true,
  "message": "Connection successful"
}
```

#### DELETE `/api/connections/{connection_id}`

Delete a connection.

**Response:**

```json
{
  "success": true
}
```

### Schemas API

#### GET `/api/schemas/{connection_id}`

Get all schemas for a connection.

**Response:**

```json
[
  {
    "name": "schema_name",
    "table_count": 10,
    "size_mb": 125.50
  }
]
```

### Clone API

#### POST `/api/clone`

Start a clone job.

**Request Body:**

```json
{
  "connection_id": "uuid",
  "source_schema": "original_schema",
  "target_schema": "backup_schema"
}
```

**Response:**

```json
{
  "success": true,
  "job_id": "uuid"
}
```

#### GET `/api/clone/status/{job_id}`

Get clone job status.

**Response:**

```json
{
  "job_id": "uuid",
  "status": "running",
  "progress": 50,
  "error_message": null,
  "start_time": "2024-01-01T12:00:00",
  "end_time": null
}
```

#### GET `/api/clone/logs/{job_id}`

Get clone job logs.

**Response:**

```json
[
  "[2024-01-01 12:00:00] [INFO] Starting clone...",
  "[2024-01-01 12:00:05] [INFO] Dump created successfully"
]
```

#### POST `/api/clone/cancel/{job_id}`

Cancel a running clone job.

**Response:**

```json
{
  "success": true
}
```

### Config API

#### GET `/api/config/mysql-bin`

Get MySQL bin path configuration.

**Response:**

```json
{
  "path": "/usr/bin"
}
```

#### POST `/api/config/mysql-bin`

Set MySQL bin path configuration.

**Request Body:**

```json
{
  "path": "/usr/bin"
}
```

**Response:**

```json
{
  "success": true
}
```

## Docker Usage

### Container Management

**Start service:**
```bash
docker-compose up -d
```

**Stop service:**
```bash
docker-compose down
```

**View logs:**
```bash
docker-compose logs -f
```

**Restart service:**
```bash
docker-compose restart
```

**Rebuild image:**
```bash
docker-compose build --no-cache
docker-compose up -d
```

### Configuration in Docker

**MySQL Binaries:**
- Pre-installed at `/app/mysql/bin` in container
- No additional configuration needed

**Persistent Data:**
- Connections: `./config.local` (volume mounted)
- Exports: `./tmp` (volume mounted)

**Environment Variables:**
```bash
# Optional customization in docker-compose.yml
environment:
  - DB_CLONE_MYSQL_BIN=/app/mysql/bin
  - FLASK_ENV=production
```

### Health Check

The container includes a health check that runs every 30 seconds:

```bash
# Check health status
docker-compose ps

# Manual health check
curl http://localhost:5000/api/health
```

## Development

### Docker Development Workflow

**Build and run in development mode:**

```bash
# Build image
docker-compose build

# Run with live code reload (mount source)
docker-compose -f docker-compose.dev.yml up
```

### Setup Development Environment

1. Clone the repository:

```bash
git clone https://github.com/melihcelenk/db-clone-tool.git
cd db-clone-tool
```

2. Install development dependencies:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

3. Install in editable mode:

```bash
pip install -e .
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src.db_clone_tool --cov-report=html

# Run specific test file
pytest tests/test_storage.py
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

### Project Structure

```
db-clone-tool/
├── src/
│   └── db_clone_tool/
│       ├── __init__.py
│       ├── main.py              # Application entry point
│       ├── config.py            # Configuration management
│       ├── storage.py            # Connection storage
│       ├── db_manager.py         # Database operations
│       ├── clone_service.py      # Cloning service
│       ├── routes/               # Flask blueprints
│       │   ├── __init__.py
│       │   ├── web.py            # Web routes
│       │   └── api.py            # API routes
│       ├── templates/            # HTML templates
│       │   └── index.html
│       └── static/               # Static files
│           ├── css/
│           │   └── style.css
│           └── js/
│               └── app.js
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_storage.py
│   ├── test_config.py
│   └── test_api.py
├── requirements.txt              # Production dependencies
├── requirements-dev.txt          # Development dependencies
├── pyproject.toml                # Project configuration
├── setup.py                      # Setup script
├── pytest.ini                    # Pytest configuration
├── LICENSE                       # MIT License
├── README.md                     # This file
├── CONTRIBUTING.md               # Contribution guidelines
└── CHANGELOG.md                  # Changelog
```

## Configuration

Configuration files are stored in `config.local/` directory (not in version control):

- `config.local/connections.json` - Saved database connections (encrypted passwords)
- `config.local/config.json` - Application configuration (MySQL bin path)

### MySQL Bin Path Configuration

**Required:** You must configure the MySQL bin path to use mysqldump/mysql commands.

**Option 1: Manual Path**
1. Click "Configure" in the right panel
2. Enter the path to your MySQL bin directory
3. Click "Test Path" to verify
4. Click "Save Configuration"

Examples:
- Windows: `C:/mysql/bin` or `C:/Program Files/mysql-8.0.40-winx64/bin`
- Linux: `/usr/bin` or `/usr/local/mysql/bin`

**Option 2: Download MySQL (Coming Soon)**
1. Click "Configure" in the right panel
2. Select MySQL version from dropdown
3. Choose destination directory
4. Click "Download & Install"
5. Path will be automatically configured

**Note:** The application does not include default MySQL paths. You must configure this before using clone/export/import features.

## API Documentation

### MySQL Management API

#### GET `/api/mysql/versions`

Get list of available MySQL versions for download.

**Response:**
```json
{
  "versions": ["8.0.40", "8.0.39", "5.7.44"],
  "recommended": "8.0.40"
}
```

#### POST `/api/mysql/validate`

Validate a MySQL installation path.

**Request Body:**
```json
{
  "path": "C:/mysql/bin"
}
```

**Response:**
```json
{
  "valid": true,
  "path": "C:/mysql/bin"
}
```

## Security

- Passwords are base64 encoded before storage (basic obfuscation)
- For production use, consider implementing stronger encryption
- Never commit `config.local/` directory to version control
- Use environment variables for sensitive data in production

## Security

- Passwords are base64 encoded before storage (basic obfuscation)
- For production use, consider implementing stronger encryption
- Never commit `connections.json` or `config.json` to version control
- Use environment variables for sensitive data in production

## Troubleshooting

### Docker Issues

**Container won't start:**
```bash
# Check logs
docker-compose logs

# Rebuild image
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

**Port 5000 already in use:**
```bash
# Change port in docker-compose.yml
ports:
  - "8080:5000"  # Use port 8080 instead
```

**Permissions issues with volumes:**
```bash
# Fix ownership (Linux/macOS)
sudo chown -R $USER:$USER config.local tmp
```

### mysqldump not found

**Problem:** Error message "mysqldump not found"

**Solution:**

1. Ensure MySQL is installed
2. Configure the MySQL bin path in the application settings
3. Verify the path contains `mysqldump.exe` (Windows) or `mysqldump` (Linux)

### Connection failed

**Problem:** Cannot connect to MySQL server

**Solution:**

1. Verify MySQL server is running
2. Check host, port, username, and password
3. Ensure MySQL user has necessary permissions
4. Check firewall settings

### Clone fails

**Problem:** Schema cloning fails with error

**Solution:**

1. Check MySQL user has CREATE DATABASE permission
2. Verify target schema name doesn't already exist (or allow overwrite)
3. Check available disk space
4. Review logs for specific error messages

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

**Melih Çelenk**

- Email: info@melihcelenk.com
- GitHub: [@melihcelenk](https://github.com/melihcelenk)

## Acknowledgments

- Built with [Flask](https://flask.palletsprojects.com/)
- Uses [pymysql](https://github.com/PyMySQL/PyMySQL) for MySQL connectivity
- Inspired by IntelliJ IDEA's database tools

## Support

- 🐛 [Report a Bug](https://github.com/melihcelenk/db-clone-tool/issues)
- 💡 [Request a Feature](https://github.com/melihcelenk/db-clone-tool/issues)
- 📖 [Documentation](https://github.com/melihcelenk/db-clone-tool#readme)

---

Made with ❤️ for developers who need to clone MySQL schemas quickly and easily.
