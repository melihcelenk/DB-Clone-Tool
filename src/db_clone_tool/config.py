"""
Configuration management for DB Clone Tool
"""
import os
import json
from pathlib import Path

# Base directory for storing config files
BASE_DIR = Path(__file__).parent.parent.parent
CONFIG_DIR = BASE_DIR / "config.local"
CONNECTIONS_FILE = CONFIG_DIR / "connections.json"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Default MySQL bin path (Windows)
DEFAULT_MYSQL_BIN_WINDOWS = r"C:\Program Files\mysql-5.7.44-winx64\bin"
DEFAULT_MYSQL_BIN_LINUX = "/usr/bin"


def get_mysql_bin_path():
    """Get MySQL bin directory path from config file"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('mysql_bin_path', '')
        except Exception:
            pass
    
    # Return default based on OS
    if os.name == 'nt':  # Windows
        return DEFAULT_MYSQL_BIN_WINDOWS
    else:  # Linux/Unix
        return DEFAULT_MYSQL_BIN_LINUX


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
    """Get full path to mysqldump executable"""
    bin_path = get_mysql_bin_path()
    if not bin_path:
        return None
    
    if os.name == 'nt':  # Windows
        return os.path.join(bin_path, 'mysqldump.exe')
    else:  # Linux/Unix
        return os.path.join(bin_path, 'mysqldump')


def get_mysql_path():
    """Get full path to mysql executable"""
    bin_path = get_mysql_bin_path()
    if not bin_path:
        return None
    
    if os.name == 'nt':  # Windows
        return os.path.join(bin_path, 'mysql.exe')
    else:  # Linux/Unix
        return os.path.join(bin_path, 'mysql')
