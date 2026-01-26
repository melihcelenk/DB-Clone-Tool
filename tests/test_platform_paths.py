"""
Tests for platform-specific default paths
"""
import pytest
import os
import platform
from pathlib import Path
from unittest.mock import patch
from src.db_clone_tool.config import get_default_mysql_dir


class TestPlatformSpecificPaths:
    """Test platform-specific default directory resolution"""

    @patch('os.name', 'nt')
    @patch.dict(os.environ, {'LOCALAPPDATA': 'C:\\Users\\TestUser\\AppData\\Local'})
    def test_windows_default_path(self):
        """Test that Windows uses %LOCALAPPDATA%\\db-clone-tool\\mysql"""
        result = get_default_mysql_dir()

        expected = Path('C:\\Users\\TestUser\\AppData\\Local') / 'db-clone-tool' / 'mysql'
        assert result == expected
        assert isinstance(result, Path)

    @patch('os.name', 'posix')
    @patch('src.db_clone_tool.config.Path.home')
    def test_linux_default_path(self, mock_home):
        """Test that Linux uses ~/.local/share/db-clone-tool/mysql"""
        from pathlib import PureWindowsPath
        # Use PureWindowsPath for cross-platform testing
        mock_home.return_value = PureWindowsPath('C:/home/testuser')

        result = get_default_mysql_dir()

        # Result will be a Path object with Linux-like structure
        assert str(result).endswith(str(PureWindowsPath('db-clone-tool/mysql')))
        assert 'db-clone-tool' in str(result)
        assert 'mysql' in str(result)

    @patch('os.name', 'posix')
    @patch('src.db_clone_tool.config.Path.home')
    def test_macos_default_path(self, mock_home):
        """Test that macOS uses ~/.local/share/db-clone-tool/mysql (same as Linux)"""
        from pathlib import PureWindowsPath
        mock_home.return_value = PureWindowsPath('C:/Users/testuser')

        result = get_default_mysql_dir()

        # Verify structure
        assert 'db-clone-tool' in str(result)
        assert 'mysql' in str(result)

    @patch('os.name', 'nt')
    @patch.dict(os.environ, {}, clear=True)
    def test_windows_fallback_when_localappdata_missing(self):
        """Test Windows fallback when LOCALAPPDATA is not set"""
        # Should use a sensible default or raise an error
        with pytest.raises((KeyError, ValueError)):
            get_default_mysql_dir()

    def test_path_is_absolute(self):
        """Test that returned path is always absolute"""
        result = get_default_mysql_dir()
        assert result.is_absolute()

    def test_path_components_correct(self):
        """Test that path contains db-clone-tool and mysql components"""
        result = get_default_mysql_dir()
        parts = result.parts

        assert 'db-clone-tool' in parts
        assert 'mysql' in parts


class TestPathCreation:
    """Test path creation and permissions"""

    def test_create_default_path_succeeds(self, tmp_path):
        """Test that default path can be created"""
        test_path = tmp_path / 'db-clone-tool' / 'mysql'
        test_path.mkdir(parents=True, exist_ok=True)

        assert test_path.exists()
        assert test_path.is_dir()

    def test_nested_directory_creation(self, tmp_path):
        """Test that nested directories are created properly"""
        test_path = tmp_path / 'level1' / 'level2' / 'level3'
        test_path.mkdir(parents=True, exist_ok=True)

        assert test_path.exists()
        assert (tmp_path / 'level1').exists()
        assert (tmp_path / 'level1' / 'level2').exists()

    def test_path_already_exists_no_error(self, tmp_path):
        """Test that creating existing path doesn't raise error"""
        test_path = tmp_path / 'existing'
        test_path.mkdir()

        # Should not raise error
        test_path.mkdir(parents=True, exist_ok=True)
        assert test_path.exists()


class TestPathValidation:
    """Test path validation"""

    def test_valid_path_validation(self, tmp_path):
        """Test validation of valid path"""
        test_path = tmp_path / 'bin'
        test_path.mkdir()

        # Create fake MySQL binaries
        (test_path / 'mysqldump.exe').touch()
        (test_path / 'mysql.exe').touch()

        # Should validate successfully
        from src.db_clone_tool.mysql_download import validate_installation
        assert validate_installation(str(test_path)) is True

    def test_invalid_path_validation(self, tmp_path):
        """Test validation of invalid path (missing binaries)"""
        test_path = tmp_path / 'bin'
        test_path.mkdir()

        # Don't create binaries
        from src.db_clone_tool.mysql_download import validate_installation
        assert validate_installation(str(test_path)) is False

    def test_nonexistent_path_validation(self):
        """Test validation of non-existent path"""
        from src.db_clone_tool.mysql_download import validate_installation
        assert validate_installation('/nonexistent/path/bin') is False
