# MySQL Schema Clone Tool

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Web-based MySQL database schema cloning tool using `mysqldump`. Clone entire database schemas with all tables, data, triggers, procedures, and events through an intuitive web interface.

## 🚀 Quick Start (Windows)

**One-click run:**

1. **Double-click** on `run.bat`
2. Packages will be installed automatically on first run
3. Browser will open automatically

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

### Prerequisites

- Python 3.8 or higher
- MySQL server with `mysqldump` and `mysql` binaries
- pip (Python package manager)

### Quick Start (Windows)

**Easiest method - Run by double-clicking:**

1. Download or clone the project
2. Double-click on `run.bat`
   - Necessary packages will be installed automatically on first run
   - Browser will open automatically
   - Application will run at `http://localhost:5000`

**Alternative - With Python file:**

- Double-click on `run.py` (performs the same function, cross-platform)

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

### Linux/Mac

```bash
python run.py
```

or

```bash
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

## Development

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

To get started, copy the example files:

```bash
# On Windows
copy config.local.example\connections.json.example config.local\connections.json
copy config.local.example\config.json.example config.local\config.json

# On Linux/Mac
cp config.local.example/connections.json.example config.local/connections.json
cp config.local.example/config.json.example config.local/config.json
```

Then edit the files with your actual configuration.

**Note:** The `config.local/` directory is automatically gitignored to protect your sensitive data.

## Security

- Passwords are base64 encoded before storage (basic obfuscation)
- For production use, consider implementing stronger encryption
- Never commit `connections.json` or `config.json` to version control
- Use environment variables for sensitive data in production

## Troubleshooting

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
