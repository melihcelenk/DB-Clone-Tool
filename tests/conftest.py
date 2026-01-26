"""
Pytest configuration and fixtures
"""
import pytest
import tempfile
import json
import os
from pathlib import Path
from src.db_clone_tool import storage, config


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary directory for config files"""
    original_connections_file = config.CONNECTIONS_FILE
    original_config_file = config.CONFIG_FILE
    
    # Set temporary paths
    config.CONNECTIONS_FILE = tmp_path / "connections.json"
    config.CONFIG_FILE = tmp_path / "config.json"
    
    yield tmp_path
    
    # Restore original paths
    config.CONNECTIONS_FILE = original_connections_file
    config.CONFIG_FILE = original_config_file


@pytest.fixture
def sample_connection():
    """Sample connection data for testing"""
    return {
        'id': 'test-connection-1',
        'name': 'Test Connection',
        'host': 'localhost',
        'port': 3306,
        'user': 'testuser',
        'password': 'testpass',
        'database': 'testdb'
    }


@pytest.fixture
def flask_app():
    """Create Flask application for testing"""
    from src.db_clone_tool.main import create_app
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(flask_app):
    """Create Flask test client"""
    return flask_app.test_client()
