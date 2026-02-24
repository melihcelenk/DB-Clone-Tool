"""
MySQL Schema Clone Tool
Web-based tool for cloning MySQL database schemas
"""
import importlib.metadata

try:
    # Try to get package name from installed package metadata
    APP_NAME = importlib.metadata.metadata('db-clone-tool')['Name']
except (importlib.metadata.PackageNotFoundError, KeyError):
    # Fallback to default if package not installed or metadata not available
    APP_NAME = 'db-clone-tool'

__version__ = "0.1.0"
