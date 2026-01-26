"""
Tests for storage module
"""
import pytest
from src.db_clone_tool import storage
from tests.conftest import temp_config_dir, sample_connection


class TestStorage:
    """Test storage operations"""
    
    def test_add_connection(self, temp_config_dir, sample_connection):
        """Test adding a connection"""
        connection_id = storage.add_connection(sample_connection)
        assert connection_id == sample_connection['id']
        
        # Verify it was saved
        connections = storage.load_connections()
        assert len(connections) == 1
        assert connections[0]['name'] == sample_connection['name']
    
    def test_load_connections_empty(self, temp_config_dir):
        """Test loading connections when none exist"""
        connections = storage.load_connections()
        assert connections == []
    
    def test_load_connections(self, temp_config_dir, sample_connection):
        """Test loading saved connections"""
        storage.add_connection(sample_connection)
        connections = storage.load_connections()
        
        assert len(connections) == 1
        assert connections[0]['name'] == sample_connection['name']
        assert connections[0]['host'] == sample_connection['host']
        # Password should be decoded
        assert connections[0]['password'] == sample_connection['password']
    
    def test_delete_connection(self, temp_config_dir, sample_connection):
        """Test deleting a connection"""
        connection_id = storage.add_connection(sample_connection)
        
        success = storage.delete_connection(connection_id)
        assert success is True
        
        connections = storage.load_connections()
        assert len(connections) == 0
    
    def test_delete_nonexistent_connection(self, temp_config_dir):
        """Test deleting a connection that doesn't exist"""
        success = storage.delete_connection('nonexistent-id')
        assert success is False
    
    def test_get_connection(self, temp_config_dir, sample_connection):
        """Test getting a specific connection"""
        connection_id = storage.add_connection(sample_connection)
        
        conn = storage.get_connection(connection_id)
        assert conn is not None
        assert conn['name'] == sample_connection['name']
    
    def test_get_nonexistent_connection(self, temp_config_dir):
        """Test getting a connection that doesn't exist"""
        conn = storage.get_connection('nonexistent-id')
        assert conn is None
    
    def test_update_connection(self, temp_config_dir, sample_connection):
        """Test updating a connection"""
        connection_id = storage.add_connection(sample_connection)
        
        updates = {'name': 'Updated Name', 'host': 'updated-host'}
        success = storage.update_connection(connection_id, updates)
        assert success is True
        
        conn = storage.get_connection(connection_id)
        assert conn['name'] == 'Updated Name'
        assert conn['host'] == 'updated-host'
