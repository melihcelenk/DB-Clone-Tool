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


class TestMySQLDownloadAPI:
    """Test MySQL download API endpoints"""

    def test_get_mysql_versions(self, client):
        """Test getting MySQL versions list"""
        response = client.get('/api/mysql/versions')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'versions' in data
        assert isinstance(data['versions'], list)
        assert len(data['versions']) > 0
        assert 'recommended' in data

    def test_validate_mysql_path_valid(self, client, temp_config_dir):
        """Test validating a valid MySQL path"""
        import tempfile
        from pathlib import Path

        # Create a temporary bin directory with fake executables
        with tempfile.TemporaryDirectory() as temp_dir:
            bin_path = Path(temp_dir) / "bin"
            bin_path.mkdir()
            (bin_path / "mysqldump.exe").touch()
            (bin_path / "mysql.exe").touch()

            response = client.post(
                '/api/mysql/validate',
                data=json.dumps({'path': str(bin_path)}),
                content_type='application/json'
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['valid'] is True

    def test_validate_mysql_path_invalid(self, client):
        """Test validating an invalid MySQL path"""
        response = client.post(
            '/api/mysql/validate',
            data=json.dumps({'path': '/nonexistent/path'}),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['valid'] is False

    def test_validate_mysql_path_missing(self, client):
        """Test validation without providing path"""
        response = client.post(
            '/api/mysql/validate',
            data=json.dumps({}),
            content_type='application/json'
        )

        assert response.status_code == 400

    def test_download_mysql_missing_version(self, client):
        """Test download without version"""
        response = client.post(
            '/api/mysql/download',
            data=json.dumps({}),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'version' in data['error'].lower()

    def test_download_mysql_with_mock(self, client, temp_config_dir, monkeypatch):
        """Test MySQL download endpoint with mocked functions"""
        from pathlib import Path
        import tempfile

        # Mock download_mysql to return a fake zip path
        def mock_download_mysql(version, dest_dir, progress_callback=None):
            # Create a fake zip file
            zip_path = Path(dest_dir) / f"mysql-{version}.zip"
            zip_path.parent.mkdir(parents=True, exist_ok=True)
            zip_path.touch()
            return str(zip_path)

        # Mock extract_mysql to return a fake bin path
        def mock_extract_mysql(zip_path, dest_dir):
            bin_path = Path(dest_dir) / "mysql-8.0.40-winx64" / "bin"
            bin_path.mkdir(parents=True, exist_ok=True)
            (bin_path / "mysqldump.exe").touch()
            (bin_path / "mysql.exe").touch()
            return str(bin_path)

        # Mock validate_installation to return True
        def mock_validate_installation(bin_path):
            return True

        # Apply mocks
        import src.db_clone_tool.routes.api as api_module
        monkeypatch.setattr(api_module, 'download_mysql', mock_download_mysql)
        monkeypatch.setattr(api_module, 'extract_mysql', mock_extract_mysql)
        monkeypatch.setattr(api_module, 'validate_installation', mock_validate_installation)

        with tempfile.TemporaryDirectory() as temp_dir:
            response = client.post(
                '/api/mysql/download',
                data=json.dumps({
                    'version': '8.0.40',
                    'destination': temp_dir
                }),
                content_type='application/json'
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'bin_path' in data
            assert data['version'] == '8.0.40'


class TestWebRoutes:
    """Test web routes"""

    def test_index_route(self, client):
        """Test index route"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'MySQL Schema Clone Tool' in response.data
