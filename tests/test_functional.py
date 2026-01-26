"""
Functional tests for application behavior
"""
import pytest
from tests.conftest import client, temp_config_dir


@pytest.mark.functional
class TestApplicationUI:
    """Test UI functionality"""

    def test_mysql_bin_path_empty_when_not_configured(self, temp_config_dir):
        """Test that MySQL bin path is empty when not configured"""
        from src.db_clone_tool import config

        # Ensure config is empty
        if config.CONFIG_FILE.exists():
            config.CONFIG_FILE.unlink()

        # Try to get bin path - should be empty
        bin_path = config.get_mysql_bin_path()
        assert bin_path == "", "MySQL bin path should be empty when not configured"

        # Trying to get mysqldump path should return None
        mysqldump_path = config.get_mysqldump_path()
        assert mysqldump_path is None, "mysqldump path should be None when bin path not configured"


@pytest.mark.functional
class TestDownloadFeature:
    """Test MySQL download functionality"""

    def test_mysql_versions_endpoint(self, client):
        """Test that MySQL versions endpoint returns valid data"""
        response = client.get('/api/mysql/versions')
        assert response.status_code == 200

        data = response.get_json()
        assert 'versions' in data
        assert isinstance(data['versions'], list)
        assert len(data['versions']) > 0
        assert 'recommended' in data
