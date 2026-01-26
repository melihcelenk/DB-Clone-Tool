"""
Tests for MySQL download service
"""
import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.db_clone_tool.mysql_download import (
    fetch_versions,
    download_mysql,
    extract_mysql,
    validate_installation
)


class TestFetchVersions:
    """Test version fetching"""

    def test_fetch_versions_returns_list(self):
        """Test that fetch_versions returns a list of versions"""
        versions = fetch_versions()
        assert isinstance(versions, list)
        assert len(versions) > 0

    def test_fetch_versions_contains_recommended(self):
        """Test that versions list contains recommended versions"""
        versions = fetch_versions()
        # Should contain major versions like 8.0, 5.7
        major_versions = [v.split('.')[0] for v in versions]
        assert '8' in major_versions

    def test_fetch_versions_format(self):
        """Test that versions are in correct format (x.y.z)"""
        versions = fetch_versions()
        for version in versions:
            parts = version.split('.')
            assert len(parts) >= 2  # At least x.y
            # All parts should be numeric
            for part in parts:
                assert part.replace('.', '').isdigit()


class TestDownloadMySQL:
    """Test MySQL downloading"""

    @patch('requests.get')
    def test_download_mysql_creates_file(self, mock_get):
        """Test that download creates a file"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'content-length': '1000'}
        mock_response.iter_content = lambda chunk_size: [b'test data']

        mock_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = download_mysql("8.0.40", temp_dir, progress_callback=None)

            assert zip_path is not None
            assert Path(zip_path).exists()
            assert zip_path.endswith('.zip')

    @patch('requests.get')
    def test_download_mysql_with_progress(self, mock_get):
        """Test that download calls progress callback"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'content-length': '100'}
        mock_response.iter_content = lambda chunk_size: [b'x' * 50, b'x' * 50]

        mock_get.return_value = mock_response

        progress_calls = []

        def progress_callback(percent):
            progress_calls.append(percent)

        with tempfile.TemporaryDirectory() as temp_dir:
            download_mysql("8.0.40", temp_dir, progress_callback=progress_callback)

            # Should have called progress callback
            assert len(progress_calls) > 0


class TestExtractMySQL:
    """Test MySQL extraction"""

    def test_extract_mysql_creates_bin_directory(self):
        """Test that extraction creates bin directory"""
        import zipfile

        # Create a mock zip file with bin directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test zip
            zip_path = Path(temp_dir) / "test-mysql.zip"
            dest_dir = Path(temp_dir) / "extracted"
            dest_dir.mkdir()

            with zipfile.ZipFile(zip_path, 'w') as zf:
                # Create bin directory structure
                zf.writestr("mysql-8.0.40-winx64/bin/", "")
                zf.writestr("mysql-8.0.40-winx64/bin/mysqldump.exe", "fake executable")

            extract_mysql(str(zip_path), str(dest_dir))

            # Check that bin directory was created
            bin_dirs = list(dest_dir.rglob("bin"))
            assert len(bin_dirs) > 0

    def test_extract_mysql_handles_errors(self):
        """Test that extraction handles errors gracefully"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with non-existent zip
            result = extract_mysql("nonexistent.zip", temp_dir)
            assert result is None


class TestValidateInstallation:
    """Test installation validation"""

    def test_validate_installation_with_valid_bin(self):
        """Test validation with valid bin directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            bin_path = Path(temp_dir) / "bin"
            bin_path.mkdir()

            # Create fake executables
            (bin_path / "mysqldump.exe").touch()
            (bin_path / "mysql.exe").touch()

            result = validate_installation(str(bin_path))
            assert result is True

    def test_validate_installation_with_missing_executables(self):
        """Test validation with missing executables"""
        with tempfile.TemporaryDirectory() as temp_dir:
            bin_path = Path(temp_dir) / "bin"
            bin_path.mkdir()

            result = validate_installation(str(bin_path))
            assert result is False

    def test_validate_installation_with_nonexistent_path(self):
        """Test validation with non-existent path"""
        result = validate_installation("/nonexistent/path")
        assert result is False
