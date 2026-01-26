"""
Tests for config module
"""
import pytest
import os
from src.db_clone_tool import config
from tests.conftest import temp_config_dir


class TestConfig:
    """Test configuration operations"""
    
    def test_get_mysql_bin_path_default(self, temp_config_dir):
        """Test getting default MySQL bin path"""
        path = config.get_mysql_bin_path()
        assert path is not None
        assert isinstance(path, str)
    
    def test_set_and_get_mysql_bin_path(self, temp_config_dir):
        """Test setting and getting MySQL bin path"""
        test_path = "/usr/local/mysql/bin"
        config.set_mysql_bin_path(test_path)
        
        path = config.get_mysql_bin_path()
        assert path == test_path
    
    def test_get_mysqldump_path(self, temp_config_dir):
        """Test getting mysqldump path"""
        test_path = "/usr/local/mysql/bin"
        config.set_mysql_bin_path(test_path)
        
        mysqldump_path = config.get_mysqldump_path()
        if os.name == 'nt':  # Windows
            assert mysqldump_path.endswith('mysqldump.exe')
        else:  # Linux/Unix
            assert mysqldump_path.endswith('mysqldump')
        assert test_path in mysqldump_path
    
    def test_get_mysql_path(self, temp_config_dir):
        """Test getting mysql path"""
        test_path = "/usr/local/mysql/bin"
        config.set_mysql_bin_path(test_path)
        
        mysql_path = config.get_mysql_path()
        if os.name == 'nt':  # Windows
            assert mysql_path.endswith('mysql.exe')
        else:  # Linux/Unix
            assert mysql_path.endswith('mysql')
        assert test_path in mysql_path
