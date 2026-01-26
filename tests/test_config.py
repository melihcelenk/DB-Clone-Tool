"""
Tests for config module
"""
import pytest
import os
from pathlib import Path
from src.db_clone_tool import config
from tests.conftest import temp_config_dir


class TestConfig:
    """Test configuration operations"""

    def test_get_mysql_bin_path_no_config(self, temp_config_dir):
        """Test getting MySQL bin path when config file doesn't exist"""
        # Ensure config file doesn't exist
        if config.CONFIG_FILE.exists():
            config.CONFIG_FILE.unlink()

        path = config.get_mysql_bin_path()
        # Should return empty string when no config (no default)
        assert path == ""

    def test_get_mysql_bin_path_with_config(self, temp_config_dir):
        """Test setting and getting MySQL bin path"""
        test_path = "/usr/local/mysql/bin"
        config.set_mysql_bin_path(test_path)

        path = config.get_mysql_bin_path()
        assert path == test_path

    def test_get_mysql_bin_path_empty_config(self, temp_config_dir):
        """Test getting MySQL bin path when config exists but path is empty"""
        # Create config with empty path
        config.set_mysql_bin_path("")

        path = config.get_mysql_bin_path()
        assert path == ""

    def test_get_mysqldump_path_no_bin(self, temp_config_dir):
        """Test getting mysqldump path when bin path is not set"""
        # Ensure config file doesn't exist
        if config.CONFIG_FILE.exists():
            config.CONFIG_FILE.unlink()

        mysqldump_path = config.get_mysqldump_path()
        # Should return None when no bin path configured
        assert mysqldump_path is None

    def test_get_mysql_path_no_bin(self, temp_config_dir):
        """Test getting mysql path when bin path is not set"""
        # Ensure config file doesn't exist
        if config.CONFIG_FILE.exists():
            config.CONFIG_FILE.unlink()

        mysql_path = config.get_mysql_path()
        # Should return None when no bin path configured
        assert mysql_path is None

    def test_get_mysqldump_path_with_bin(self, temp_config_dir):
        """Test getting mysqldump path when bin path is set"""
        test_path = "/usr/local/mysql/bin"
        config.set_mysql_bin_path(test_path)

        mysqldump_path = config.get_mysqldump_path()
        if os.name == 'nt':  # Windows
            assert mysqldump_path.endswith('mysqldump.exe')
        else:  # Linux/Unix
            assert mysqldump_path.endswith('mysqldump')
        assert test_path in mysqldump_path

    def test_get_mysql_path_with_bin(self, temp_config_dir):
        """Test getting mysql path when bin path is set"""
        test_path = "/usr/local/mysql/bin"
        config.set_mysql_bin_path(test_path)

        mysql_path = config.get_mysql_path()
        if os.name == 'nt':  # Windows
            assert mysql_path.endswith('mysql.exe')
        else:  # Linux/Unix
            assert mysql_path.endswith('mysql')
        assert test_path in mysql_path
