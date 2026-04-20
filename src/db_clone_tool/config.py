"""
Configuration management for DB Clone Tool
"""
import os
import json
from pathlib import Path
from src.db_clone_tool import APP_NAME

# Base directory for storing config files
BASE_DIR = Path(__file__).parent.parent.parent
CONFIG_DIR = Path(os.environ.get('DB_CLONE_CONFIG_DIR', '')) if os.environ.get('DB_CLONE_CONFIG_DIR') else BASE_DIR / "config.local"
CONNECTIONS_FILE = CONFIG_DIR / "connections.json"
CONFIG_FILE = CONFIG_DIR / "config.json"


def get_default_mysql_dir():
    """Get platform-specific default MySQL installation directory

    Returns:
        Path: Platform-specific default path for MySQL binaries
            - Windows: %LOCALAPPDATA%\\{APP_NAME}\\mysql
            - Linux/macOS: ~/.local/share/{APP_NAME}/mysql

    Raises:
        KeyError: If required environment variable is not set (Windows: LOCALAPPDATA)
    """
    if os.name == 'nt':  # Windows
        # Use LOCALAPPDATA for user-specific portable install
        local_app_data = os.environ['LOCALAPPDATA']
        return Path(local_app_data) / APP_NAME / 'mysql'
    else:  # Linux, macOS, other Unix-like
        # Use XDG-like path: ~/.local/share
        return Path.home() / '.local' / 'share' / APP_NAME / 'mysql'

def get_default_postgres_dir():
    """Get platform-specific default PostgreSQL installation directory

    Returns:
        Path: Platform-specific default path for PG binaries
            - Windows: %LOCALAPPDATA%\\{APP_NAME}\\postgres
            - Linux/macOS: ~/.local/share/{APP_NAME}/postgres
    """
    if os.name == 'nt':
        local_app_data = os.environ['LOCALAPPDATA']
        return Path(local_app_data) / APP_NAME / 'postgres'
    return Path.home() / '.local' / 'share' / APP_NAME / 'postgres'


def get_mysql_bin_path():
    """Get MySQL bin directory path from config file or environment variable.

    Priority:
        1. config.json file (explicit user choice via UI)
        2. DB_CLONE_MYSQL_BIN environment variable (Docker/production default)

    Returns:
        str: MySQL bin path if configured, empty string otherwise
    """
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                path = config_data.get('mysql_bin_path', '')
                if path:
                    return path
        except Exception:
            pass

    env_path = os.environ.get('DB_CLONE_MYSQL_BIN', '')
    if env_path and Path(env_path).exists():
        return env_path

    return ''


def set_mysql_bin_path(path):
    """Save MySQL bin directory path to config file"""
    config = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass
    
    config['mysql_bin_path'] = path
    
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)


def get_mysqldump_path():
    """Get full path to mysqldump executable

    Returns:
        str or None: Full path to mysqldump executable, or None if not configured
    """
    bin_path = get_mysql_bin_path()
    if not bin_path:
        return None

    if os.name == 'nt':  # Windows
        return os.path.join(bin_path, 'mysqldump.exe')
    else:  # Linux/Unix
        return os.path.join(bin_path, 'mysqldump')


def get_mysql_path():
    """Get full path to mysql executable

    Returns:
        str or None: Full path to mysql executable, or None if not configured
    """
    bin_path = get_mysql_bin_path()
    if not bin_path:
        return None

    if os.name == 'nt':  # Windows
        return os.path.join(bin_path, 'mysql.exe')
    else:  # Linux/Unix
        return os.path.join(bin_path, 'mysql')


def get_postgres_bin_path():
    """Get PostgreSQL bin directory path from config file or environment variable.

    Priority:
        1. config.json: postgres_bin_path (explicit user choice via UI)
        2. DB_CLONE_POSTGRES_BIN environment variable (Docker/production default)
    """
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                path = config_data.get('postgres_bin_path', '')
                if path:
                    return path
        except Exception:
            pass

    env_path = os.environ.get('DB_CLONE_POSTGRES_BIN', '')
    if env_path and Path(env_path).exists():
        return env_path

    return ''


def set_postgres_bin_path(path):
    """Save PostgreSQL bin directory path to config file."""
    config = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass

    config['postgres_bin_path'] = path

    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)


def _pg_exe_name(name):
    """Windows adds .exe; elsewhere bare name."""
    return f"{name}.exe" if os.name == 'nt' else name


def get_pg_dump_path():
    bin_path = get_postgres_bin_path()
    if not bin_path:
        return None
    return os.path.join(bin_path, _pg_exe_name('pg_dump'))


def get_pg_restore_path():
    bin_path = get_postgres_bin_path()
    if not bin_path:
        return None
    return os.path.join(bin_path, _pg_exe_name('pg_restore'))


def get_psql_path():
    bin_path = get_postgres_bin_path()
    if not bin_path:
        return None
    return os.path.join(bin_path, _pg_exe_name('psql'))


def validate_postgres_bin_path(bin_path):
    """Validate PostgreSQL bin directory path.

    Returns (is_valid, error_message). Required binaries: pg_dump, pg_restore, psql.
    """
    if not bin_path:
        return False, "PostgreSQL bin path is not configured. Please configure it in settings."

    bin_dir = Path(bin_path)
    if not bin_dir.exists():
        return False, "Directory does not exist. Please check the path and try again."
    if not bin_dir.is_dir():
        return False, "Path is not a directory. Please provide a directory path."

    required = ['pg_dump', 'pg_restore', 'psql']
    for name in required:
        exe = bin_dir / _pg_exe_name(name)
        if not exe.exists():
            return False, f"{name} not found in the specified directory. Please ensure PostgreSQL client binaries are present."

    return True, None


def validate_mysql_bin_path(bin_path):
    """Validate MySQL bin directory path

    Args:
        bin_path: Path to MySQL bin directory

    Returns:
        tuple: (is_valid, error_message)
            - is_valid: True if path is valid, False otherwise
            - error_message: User-friendly error message if invalid, None if valid
    """
    if not bin_path:
        return False, "MySQL bin path is not configured. Please configure it in settings."

    bin_dir = Path(bin_path)

    if not bin_dir.exists():
        return False, f"Directory does not exist. Please check the path and try again."

    if not bin_dir.is_dir():
        return False, "Path is not a directory. Please provide a directory path."

    # Check for required executables
    if os.name == 'nt':  # Windows
        mysqldump = bin_dir / 'mysqldump.exe'
        mysql = bin_dir / 'mysql.exe'
    else:  # Linux/Unix
        mysqldump = bin_dir / 'mysqldump'
        mysql = bin_dir / 'mysql'

    if not mysqldump.exists():
        return False, f"mysqldump not found in the specified directory. Please ensure MySQL binaries are present."

    if not mysql.exists():
        return False, f"mysql not found in the specified directory. Please ensure MySQL binaries are present."

    return True, None


def create_directory_with_fallback(path):
    """Create directory with fallback to user directory on permission error

    Args:
        path: Path object to create

    Returns:
        tuple: (success, created_path, error_message)
            - success: True if directory created or exists
            - created_path: Actual path created (may differ from input if fallback used)
            - error_message: Error message if failed, None if success
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True, path, None
    except PermissionError:
        # Try fallback to user home directory
        fallback_path = Path.home() / f'.{APP_NAME}' / path.name
        try:
            fallback_path.mkdir(parents=True, exist_ok=True)
            return True, fallback_path, f"Using fallback directory: {fallback_path}"
        except Exception as e:
            return False, None, f"Cannot create directory. Please choose a location where you have write permissions."
    except Exception as e:
        return False, None, f"Cannot create directory: {str(e)}"
