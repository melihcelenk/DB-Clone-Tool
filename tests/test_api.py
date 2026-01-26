"""
Tests for API routes
"""
import pytest
import json
from tests.conftest import flask_app, client, temp_config_dir, sample_connection


class TestConnectionsAPI:
    """Test connections API endpoints"""
    
    def test_get_connections_empty(self, client, temp_config_dir):
        """Test getting connections when none exist"""
        response = client.get('/api/connections')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == []
    
    def test_add_connection(self, client, temp_config_dir):
        """Test adding a connection"""
        connection_data = {
            'name': 'Test DB',
            'host': 'localhost',
            'port': 3306,
            'user': 'testuser',
            'password': 'testpass',
            'database': 'testdb'
        }
        
        response = client.post(
            '/api/connections',
            data=json.dumps(connection_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'connection_id' in data
    
    def test_add_connection_missing_fields(self, client, temp_config_dir):
        """Test adding connection with missing required fields"""
        connection_data = {
            'name': 'Test DB',
            'host': 'localhost'
            # Missing port, user, password
        }
        
        response = client.post(
            '/api/connections',
            data=json.dumps(connection_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'error' in data
    
    def test_delete_connection(self, client, temp_config_dir, sample_connection):
        """Test deleting a connection"""
        from src.db_clone_tool import storage
        connection_id = storage.add_connection(sample_connection)
        
        response = client.delete(f'/api/connections/{connection_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True


class TestConfigAPI:
    """Test configuration API endpoints"""
    
    def test_get_mysql_bin_config(self, client, temp_config_dir):
        """Test getting MySQL bin config"""
        response = client.get('/api/config/mysql-bin')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'path' in data
    
    def test_set_mysql_bin_config(self, client, temp_config_dir):
        """Test setting MySQL bin config"""
        config_data = {'path': '/usr/local/mysql/bin'}
        
        response = client.post(
            '/api/config/mysql-bin',
            data=json.dumps(config_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
    
    def test_set_mysql_bin_config_missing_path(self, client, temp_config_dir):
        """Test setting config without path"""
        response = client.post(
            '/api/config/mysql-bin',
            data=json.dumps({}),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False


class TestWebRoutes:
    """Test web routes"""
    
    def test_index_route(self, client):
        """Test index route"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'MySQL Schema Clone Tool' in response.data
