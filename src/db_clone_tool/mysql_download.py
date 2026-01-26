"""
MySQL Download Service
Handles downloading, extracting, and validating MySQL installations
"""
import os
import zipfile
import requests
from pathlib import Path
from typing import List, Optional, Callable


# Hardcoded list of stable MySQL versions (more reliable than web scraping)
MYSQL_VERSIONS = [
    "8.0.40",
    "8.0.39",
    "8.0.38",
    "8.4.0",
    "8.3.0",
    "5.7.44",
]

RECOMMENDED_VERSION = "8.0.40"


def fetch_versions() -> List[str]:
    """
    Fetch list of available MySQL versions

    Returns:
        List of version strings (e.g., ["8.0.40", "8.0.39", ...])
    """
    return MYSQL_VERSIONS.copy()


def download_mysql(
    version: str,
    dest_dir: str,
    progress_callback: Optional[Callable[[int], None]] = None
) -> Optional[str]:
    """
    Download MySQL ZIP archive for specified version

    Args:
        version: MySQL version (e.g., "8.0.40")
        dest_dir: Directory to save the ZIP file
        progress_callback: Optional callback function for progress updates (receives percent 0-100)

    Returns:
        Path to downloaded ZIP file, or None if failed
    """
    try:
        # Determine platform and build URL
        is_windows = os.name == 'nt'

        if is_windows:
            # Windows x64 ZIP archive
            url = f"https://dev.mysql.com/get/Downloads/MySQL-{version.split('.')[0]}.{version.split('.')[1]}/mysql-{version}-winx64.zip"
        else:
            # Linux generic (not recommended, should use package manager)
            url = f"https://dev.mysql.com/get/Downloads/MySQL-{version.split('.')[0]}.{version.split('.')[1]}/mysql-{version}-linux-glibc2.28-x86_64.tar.xz"

        # Ensure destination directory exists
        dest_path = Path(dest_dir)
        dest_path.mkdir(parents=True, exist_ok=True)

        # Determine filename
        filename = f"mysql-{version}.zip" if is_windows else f"mysql-{version}.tar.xz"
        zip_path = dest_path / filename

        # Download with progress tracking
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Report progress
                    if progress_callback and total_size > 0:
                        percent = int((downloaded / total_size) * 100)
                        progress_callback(percent)

        return str(zip_path)

    except Exception as e:
        print(f"Download failed: {e}")
        return None


def extract_mysql(zip_path: str, dest_dir: str) -> Optional[str]:
    """
    Extract MySQL ZIP archive to destination directory

    Args:
        zip_path: Path to ZIP file
        dest_dir: Directory to extract to

    Returns:
        Path to extracted bin directory, or None if failed
    """
    try:
        zip_file = Path(zip_path)
        dest_path = Path(dest_dir)

        if not zip_file.exists():
            print(f"ZIP file not found: {zip_path}")
            return None

        # Extract ZIP
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(dest_path)

        # Find the bin directory
        # MySQL ZIP structure: mysql-x.y.z-winx64/bin/
        extracted_dirs = [d for d in dest_path.iterdir() if d.is_dir()]

        for extracted_dir in extracted_dirs:
            bin_dir = extracted_dir / "bin"
            if bin_dir.exists() and (bin_dir / "mysqldump.exe").exists():
                return str(bin_dir)

        # If standard structure not found, return first directory with bin
        for extracted_dir in extracted_dirs:
            bin_dir = extracted_dir / "bin"
            if bin_dir.exists():
                return str(bin_dir)

        return None

    except Exception as e:
        print(f"Extraction failed: {e}")
        return None


def validate_installation(bin_path: str) -> bool:
    """
    Validate MySQL installation by checking for required executables

    Args:
        bin_path: Path to MySQL bin directory

    Returns:
        True if valid installation, False otherwise
    """
    try:
        bin_dir = Path(bin_path)

        if not bin_dir.exists():
            return False

        # Check for required executables
        if os.name == 'nt':  # Windows
            required_files = ['mysqldump.exe', 'mysql.exe']
        else:  # Linux/Unix
            required_files = ['mysqldump', 'mysql']

        for filename in required_files:
            if not (bin_dir / filename).exists():
                return False

        return True

    except Exception:
        return False
