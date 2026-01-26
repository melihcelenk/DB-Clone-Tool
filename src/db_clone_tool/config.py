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
