"""
Integration tests for DBC-2 features
"""
import pytest
import os
from pathlib import Path
from unittest.mock import patch
from src.db_clone_tool.config import (
    get_default_mysql_dir,
    validate_mysql_bin_path,
    create_directory_with_fallback
)
from src.db_clone_tool.mysql_download import extract_mysql


class TestPlatformIntegration:
    """Integration tests for platform-specific features"""

    def test_default_path_resolution_windows(self):
        """Test default path resolution on Windows"""
        if os.name != 'nt':
            pytest.skip("Windows-only test")

        path = get_default_mysql_dir()
        assert path.is_absolute()
        assert 'db-clone-tool' in str(path)
        assert 'mysql' in str(path)
        # Should contain LOCALAPPDATA
        assert 'AppData' in str(path) or 'Local' in str(path)

    @patch('os.name', 'posix')
    @patch('src.db_clone_tool.config.Path.home')
    def test_default_path_resolution_linux(self, mock_home):
        """Test default path resolution on Linux"""
        from pathlib import PureWindowsPath
        mock_home.return_value = PureWindowsPath('C:/home/user')

        path = get_default_mysql_dir()
        assert 'db-clone-tool' in str(path)
        assert 'mysql' in str(path)


class TestPathValidation:
    """Integration tests for path validation"""

    def test_validate_empty_path(self):
        """Test validation of empty path"""
        is_valid, error_msg = validate_mysql_bin_path("")
        assert not is_valid
        assert "not configured" in error_msg.lower()

    def test_validate_nonexistent_path(self):
        """Test validation of non-existent path"""
        is_valid, error_msg = validate_mysql_bin_path("/nonexistent/path")
        assert not is_valid
        assert "does not exist" in error_msg.lower()

    def test_validate_valid_path(self, tmp_path):
        """Test validation of valid MySQL bin path"""
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()

        # Create fake binaries
        if os.name == 'nt':
            (bin_dir / "mysqldump.exe").touch()
            (bin_dir / "mysql.exe").touch()
        else:
            (bin_dir / "mysqldump").touch()
            (bin_dir / "mysql").touch()

        is_valid, error_msg = validate_mysql_bin_path(str(bin_dir))
        assert is_valid
        assert error_msg is None

    def test_validate_path_missing_binaries(self, tmp_path):
        """Test validation of path with missing binaries"""
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()

        is_valid, error_msg = validate_mysql_bin_path(str(bin_dir))
        assert not is_valid
        assert "not found" in error_msg.lower()


class TestDirectoryCreationFallback:
    """Integration tests for directory creation with fallback"""

    def test_create_directory_success(self, tmp_path):
        """Test successful directory creation"""
        test_dir = tmp_path / "test_mysql"
        success, created_path, error_msg = create_directory_with_fallback(test_dir)

        assert success
        assert created_path == test_dir
        assert created_path.exists()
        assert error_msg is None

    def test_create_nested_directory(self, tmp_path):
        """Test nested directory creation"""
        nested_dir = tmp_path / "level1" / "level2" / "mysql"
        success, created_path, error_msg = create_directory_with_fallback(nested_dir)

        assert success
        assert created_path.exists()
        assert (tmp_path / "level1").exists()
        assert (tmp_path / "level1" / "level2").exists()

    def test_directory_already_exists(self, tmp_path):
        """Test creating already existing directory"""
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()

        success, created_path, error_msg = create_directory_with_fallback(existing_dir)

        assert success
        assert created_path == existing_dir
        assert error_msg is None


class TestExtractionIntegration:
    """Integration tests for archive extraction"""

    def test_extract_zip_and_validate(self, tmp_path):
        """Test ZIP extraction and validation workflow"""
        import zipfile

        # Create ZIP archive
        archive_path = tmp_path / "mysql.zip"
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()

        with zipfile.ZipFile(archive_path, 'w') as zf:
            if os.name == 'nt':
                zf.writestr("mysql-8.0.40-winx64/bin/mysqldump.exe", "fake")
                zf.writestr("mysql-8.0.40-winx64/bin/mysql.exe", "fake")
            else:
                zf.writestr("mysql-8.0.40-linux/bin/mysqldump", "fake")
                zf.writestr("mysql-8.0.40-linux/bin/mysql", "fake")

        # Extract
        bin_path = extract_mysql(str(archive_path), str(extract_dir))
        assert bin_path is not None
        assert Path(bin_path).exists()

        # Validate
        is_valid, error_msg = validate_mysql_bin_path(bin_path)
        assert is_valid
        assert error_msg is None

    def test_extract_tarxz_and_validate(self, tmp_path):
        """Test tar.xz extraction and validation workflow"""
        import tarfile

        archive_path = tmp_path / "mysql.tar.xz"
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()

        # Create tar.xz with platform-appropriate binaries
        is_windows = os.name == 'nt'
        mysqldump_name = "mysqldump.exe" if is_windows else "mysqldump"
        mysql_name = "mysql.exe" if is_windows else "mysql"

        with tarfile.open(archive_path, 'w:xz') as tar:
            bin_dir = tmp_path / "mysql-8.0.40" / "bin"
            bin_dir.mkdir(parents=True)
            (bin_dir / mysqldump_name).touch()
            (bin_dir / mysql_name).touch()
            tar.add(bin_dir.parent, arcname=bin_dir.parent.name)

        # Extract
        bin_path = extract_mysql(str(archive_path), str(extract_dir))
        assert bin_path is not None

        # Validate
        is_valid, error_msg = validate_mysql_bin_path(bin_path)
        assert is_valid


class TestHealthCheckIntegration:
    """Integration tests for health check endpoint"""

    def test_health_check_endpoint(self, client):
        """Test health check endpoint returns correct response"""
        response = client.get('/api/health')
        assert response.status_code == 200

        data = response.get_json()
        assert data['status'] == 'healthy'
        assert data['service'] == 'db-clone-tool'
        assert 'version' in data


class TestEndToEndWorkflow:
    """End-to-end integration tests"""

    def test_mysql_download_workflow(self, tmp_path):
        """Test complete MySQL download and setup workflow"""
        # This test simulates the full workflow:
        # 1. Get default path
        # 2. Create directory with fallback
        # 3. Validate path after setup

        # Step 1: Get default path
        default_path = get_default_mysql_dir()
        assert default_path is not None

        # Step 2: Use tmp_path as custom location
        custom_path = tmp_path / "db-clone-tool" / "mysql"
        success, created_path, _ = create_directory_with_fallback(custom_path)
        assert success
        assert created_path.exists()

        # Step 3: Simulate binary installation
        bin_dir = created_path / "bin"
        bin_dir.mkdir()

        if os.name == 'nt':
            (bin_dir / "mysqldump.exe").touch()
            (bin_dir / "mysql.exe").touch()
        else:
            (bin_dir / "mysqldump").touch()
            (bin_dir / "mysql").touch()

        # Step 4: Validate
        is_valid, error_msg = validate_mysql_bin_path(str(bin_dir))
        assert is_valid
        assert error_msg is None
