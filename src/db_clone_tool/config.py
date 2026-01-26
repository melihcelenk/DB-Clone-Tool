"""
Configuration management for DB Clone Tool
"""
import os
import json
from pathlib import Path
from src.db_clone_tool import APP_NAME

# Base directory for storing config files
BASE_DIR = Path(__file__).parent.parent.parent
CONFIG_DIR = BASE_DIR / "config.local"
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

def get_mysql_bin_path():
    """Get MySQL bin directory path from config file

    Returns:
        str: MySQL bin path if configured, empty string otherwise
    """
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                return config_data.get('mysql_bin_path', '')
        except Exception:
            pass

    # No default - user must configure
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
