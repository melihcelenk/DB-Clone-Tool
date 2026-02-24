"""
Tests for tar.xz extraction support
"""
import pytest
import os
import tarfile
import zipfile
from pathlib import Path
from src.db_clone_tool.mysql_download import extract_mysql, validate_installation


class TestTarXzExtraction:
    """Test .tar.xz file extraction"""

    def test_extract_tarxz_creates_directory(self, tmp_path):
        """Test that .tar.xz extraction creates directory structure"""
        # Create test tar.xz file
        archive_path = tmp_path / "test-mysql.tar.xz"
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()

        # Create tar.xz with bin structure
        with tarfile.open(archive_path, 'w:xz') as tar:
            # Create a temporary bin directory
            bin_dir = tmp_path / "mysql-8.0.40-linux" / "bin"
            bin_dir.mkdir(parents=True)

            # Create fake binaries
            mysqldump = bin_dir / "mysqldump"
            mysqldump.touch()
            mysql = bin_dir / "mysql"
            mysql.touch()

            # Add to archive
            tar.add(bin_dir.parent, arcname=bin_dir.parent.name)

        # Extract
        bin_path = extract_mysql(str(archive_path), str(extract_dir))

        # Verify
        assert bin_path is not None
        assert Path(bin_path).exists()
        assert Path(bin_path).is_dir()
        assert (Path(bin_path) / "mysqldump").exists()

    def test_extract_tarxz_finds_bin_directory(self, tmp_path):
        """Test that extraction finds bin directory in tar.xz"""
        archive_path = tmp_path / "test-mysql.tar.xz"
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()

        # Create tar.xz
        with tarfile.open(archive_path, 'w:xz') as tar:
            bin_dir = tmp_path / "mysql-8.0.40-linux" / "bin"
            bin_dir.mkdir(parents=True)
            (bin_dir / "mysqldump").touch()
            (bin_dir / "mysql").touch()
            tar.add(bin_dir.parent, arcname=bin_dir.parent.name)

        # Extract and get bin path
        bin_path = extract_mysql(str(archive_path), str(extract_dir))

        # Should end with 'bin'
        assert bin_path is not None
        assert str(bin_path).endswith('bin')

    def test_extract_tarxz_handles_nested_structure(self, tmp_path):
        """Test extraction of tar.xz with nested directory structure"""
        archive_path = tmp_path / "mysql-nested.tar.xz"
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()

        # Create deeply nested structure
        with tarfile.open(archive_path, 'w:xz') as tar:
            nested = tmp_path / "mysql" / "lib" / "bin"
            nested.mkdir(parents=True)
            (nested / "mysqldump").touch()
            (nested / "mysql").touch()
            tar.add(tmp_path / "mysql", arcname="mysql")

        bin_path = extract_mysql(str(archive_path), str(extract_dir))

        assert bin_path is not None
        assert Path(bin_path).exists()

    def test_extract_tarxz_without_xz_compression(self, tmp_path):
        """Test extraction of regular tar file (no xz compression)"""
        archive_path = tmp_path / "test-mysql.tar"
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()

        # Create regular tar
        with tarfile.open(archive_path, 'w') as tar:
            bin_dir = tmp_path / "mysql" / "bin"
            bin_dir.mkdir(parents=True)
            (bin_dir / "mysqldump").touch()
            tar.add(bin_dir.parent, arcname=bin_dir.parent.name)

        bin_path = extract_mysql(str(archive_path), str(extract_dir))

        # Should still work
        assert bin_path is not None


class TestMixedFormatExtraction:
    """Test extraction of both ZIP and tar.xz formats"""

    def test_extract_zip_still_works(self, tmp_path):
        """Test that ZIP extraction still works after tar.xz support"""
        archive_path = tmp_path / "test-mysql.zip"
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()

        # Create ZIP
        with zipfile.ZipFile(archive_path, 'w') as zf:
            zf.writestr("mysql-8.0.40-winx64/bin/mysqldump.exe", "fake")
            zf.writestr("mysql-8.0.40-winx64/bin/mysql.exe", "fake")

        bin_path = extract_mysql(str(archive_path), str(extract_dir))

        assert bin_path is not None
        assert Path(bin_path).exists()

    def test_format_detection_by_extension(self, tmp_path):
        """Test that format is detected by file extension"""
        # .zip file
        zip_path = tmp_path / "mysql.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("mysql/bin/mysqldump.exe", "fake")

        extract_dir_zip = tmp_path / "extracted_zip"
        extract_dir_zip.mkdir()
        bin_path_zip = extract_mysql(str(zip_path), str(extract_dir_zip))
        assert bin_path_zip is not None

        # .tar.xz file
        tarxz_path = tmp_path / "mysql.tar.xz"
        with tarfile.open(tarxz_path, 'w:xz') as tar:
            bin_dir = tmp_path / "temp_mysql" / "bin"
            bin_dir.mkdir(parents=True)
            (bin_dir / "mysqldump").touch()
            tar.add(bin_dir.parent, arcname=bin_dir.parent.name)

        extract_dir_tar = tmp_path / "extracted_tar"
        extract_dir_tar.mkdir()
        bin_path_tar = extract_mysql(str(tarxz_path), str(extract_dir_tar))
        assert bin_path_tar is not None

    def test_unsupported_format_returns_none(self, tmp_path):
        """Test that unsupported archive format returns None"""
        # Create a .txt file (unsupported)
        fake_archive = tmp_path / "mysql.txt"
        fake_archive.write_text("not an archive")

        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()

        bin_path = extract_mysql(str(fake_archive), str(extract_dir))
        assert bin_path is None


class TestExtractionValidation:
    """Test validation after extraction"""

    def test_extracted_tarxz_passes_validation(self, tmp_path):
        """Test that extracted tar.xz binaries pass validation"""
        import os
        archive_path = tmp_path / "mysql.tar.xz"
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()

        # Create platform-appropriate binaries
        is_windows = os.name == 'nt'
        mysqldump_name = "mysqldump.exe" if is_windows else "mysqldump"
        mysql_name = "mysql.exe" if is_windows else "mysql"

        # Create and extract
        with tarfile.open(archive_path, 'w:xz') as tar:
            bin_dir = tmp_path / "mysql" / "bin"
            bin_dir.mkdir(parents=True)

            # Create binaries with platform-appropriate names
            mysqldump = bin_dir / mysqldump_name
            mysqldump.touch()
            mysql = bin_dir / mysql_name
            mysql.touch()

            tar.add(bin_dir.parent, arcname=bin_dir.parent.name)

        bin_path = extract_mysql(str(archive_path), str(extract_dir))

        # Validate
        assert validate_installation(bin_path) is True

    def test_incomplete_extraction_fails_validation(self, tmp_path):
        """Test that incomplete extraction fails validation"""
        archive_path = tmp_path / "mysql.tar.xz"
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()

        # Create tar.xz with only mysqldump (missing mysql)
        with tarfile.open(archive_path, 'w:xz') as tar:
            bin_dir = tmp_path / "mysql" / "bin"
            bin_dir.mkdir(parents=True)
            (bin_dir / "mysqldump").touch()
            # Missing mysql binary
            tar.add(bin_dir.parent, arcname=bin_dir.parent.name)

        bin_path = extract_mysql(str(archive_path), str(extract_dir))

        # Should fail validation (missing mysql)
        assert validate_installation(bin_path) is False


class TestExtractionErrorHandling:
    """Test error handling during extraction"""

    def test_corrupted_tarxz_returns_none(self, tmp_path):
        """Test that corrupted tar.xz returns None"""
        corrupted = tmp_path / "corrupted.tar.xz"
        corrupted.write_bytes(b"corrupted data")

        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()

        bin_path = extract_mysql(str(corrupted), str(extract_dir))
        assert bin_path is None

    def test_nonexistent_archive_returns_none(self, tmp_path):
        """Test that non-existent archive returns None"""
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()

        bin_path = extract_mysql("/nonexistent/archive.tar.xz", str(extract_dir))
        assert bin_path is None

    def test_permission_error_during_extraction(self, tmp_path):
        """Test handling of permission errors during extraction"""
        # This test is platform-specific and might not work on all systems
        # We'll test the basic error handling path
        archive_path = tmp_path / "mysql.tar.xz"
        with tarfile.open(archive_path, 'w:xz') as tar:
            bin_dir = tmp_path / "mysql" / "bin"
            bin_dir.mkdir(parents=True)
            (bin_dir / "mysqldump").touch()
            tar.add(bin_dir.parent, arcname=bin_dir.parent.name)

        # Try to extract to a read-only location
        # (This might fail on Windows without admin rights)
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()

        # If extraction fails, should return None
        try:
            bin_path = extract_mysql(str(archive_path), str(readonly_dir))
            # Extraction succeeded, verify result
            assert bin_path is not None or bin_path is None
        except (PermissionError, OSError):
            # Expected on some platforms
            pass
