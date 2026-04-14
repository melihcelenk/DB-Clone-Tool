"""
PostgreSQL client binaries downloader (DBC-3).

Mirrors mysql_download.py for the Postgres side. Uses EnterpriseDB's public
binary bundle (`postgresql-{version}-{build}-windows-x64-binaries.zip`) on
Windows. On Linux / macOS, PostgreSQL client tools are distributed via system
package managers; we don't auto-download there — the UI informs the user.

The "bin path" produced by this module is the directory containing pg_dump,
pg_restore and psql — same shape as MySQL's `bin/`.
"""
import os
import re
import zipfile
import requests
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any


# EDB keeps older builds online under stable URLs. Each entry pins the
# last known-good Windows build. If EDB ever bumps the -N suffix and
# invalidates the URL, the download fails cleanly and the user falls back
# to the "Manual Path" option (same UX as MySQL).
#
# Source: https://www.enterprisedb.com/download-postgresql-binaries
POSTGRES_VERSIONS: Dict[str, Dict[str, Optional[str]]] = {
    "17.2":  {"windows": "https://get.enterprisedb.com/postgresql/postgresql-17.2-1-windows-x64-binaries.zip"},
    "17.0":  {"windows": "https://get.enterprisedb.com/postgresql/postgresql-17.0-1-windows-x64-binaries.zip"},
    "16.6":  {"windows": "https://get.enterprisedb.com/postgresql/postgresql-16.6-1-windows-x64-binaries.zip"},
    "16.4":  {"windows": "https://get.enterprisedb.com/postgresql/postgresql-16.4-1-windows-x64-binaries.zip"},
    "15.10": {"windows": "https://get.enterprisedb.com/postgresql/postgresql-15.10-1-windows-x64-binaries.zip"},
    "14.15": {"windows": "https://get.enterprisedb.com/postgresql/postgresql-14.15-1-windows-x64-binaries.zip"},
    "13.18": {"windows": "https://get.enterprisedb.com/postgresql/postgresql-13.18-1-windows-x64-binaries.zip"},
}

RECOMMENDED_VERSION = "16.6"  # Stable, widely deployed, matches most hStroke test envs.


def fetch_versions() -> List[str]:
    """Return available PostgreSQL versions, newest first."""
    return sorted(POSTGRES_VERSIONS.keys(), key=_version_sort_key, reverse=True)


def _version_sort_key(v: str):
    try:
        return tuple(map(int, v.split('.')))
    except (ValueError, AttributeError):
        return (0, 0, 0)


def _get_url_for_version(version: str) -> Optional[str]:
    """Return the download URL for the current OS or None if unsupported."""
    entry = POSTGRES_VERSIONS.get(version)
    if not entry:
        return None
    if os.name == 'nt':
        return entry.get('windows')
    # Linux / macOS: EDB binaries are Windows-only in our catalog.
    # On these platforms the Docker image / package manager provides
    # pg_dump natively, so no download is wired up here.
    return None


def is_download_supported() -> bool:
    """True if we can auto-download on the current OS."""
    return os.name == 'nt'


def download_postgres(
    version: str,
    dest_dir: str,
    progress_callback: Optional[Callable[[int], None]] = None,
) -> Optional[str]:
    """Download the Postgres client zip for `version` into `dest_dir`.

    Returns the absolute path to the downloaded archive, or None on failure.
    The callback receives an integer percent (0..100) as the download streams.
    """
    try:
        url = _get_url_for_version(version)
        if not url:
            print(
                f"Download not supported for version={version} on this OS. "
                f"Use the package manager (apt/brew) to install postgresql-client."
            )
            return None

        filename = f"postgresql-{version}.zip"
        dest_path = Path(dest_dir)
        dest_path.mkdir(parents=True, exist_ok=True)
        zip_path = dest_path / filename

        # EDB redirects; requests follows them by default.
        response = requests.get(url, stream=True, timeout=30, allow_redirects=True)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_size > 0:
                        percent = int((downloaded / total_size) * 100)
                        progress_callback(percent)

        return str(zip_path)
    except Exception as e:
        print(f"PostgreSQL download failed: {e}")
        return None


def extract_postgres(archive_path: str, dest_dir: str) -> Optional[str]:
    """Extract the EDB Postgres zip and return the path to its bin/ directory.

    The EDB bundle extracts to a top-level `pgsql/` folder that contains
    `bin/`, `include/`, `lib/`, `share/`, `doc/` etc. We search recursively
    for a bin directory that contains pg_dump.
    """
    try:
        archive_file = Path(archive_path)
        dest_path = Path(dest_dir)
        if not archive_file.exists():
            print(f"Archive file not found: {archive_path}")
            return None

        if archive_path.endswith('.zip'):
            with zipfile.ZipFile(archive_file, 'r') as zf:
                zf.extractall(dest_path)
        else:
            print(f"Unsupported archive format: {archive_path}")
            return None

        # Find the bin directory containing pg_dump
        is_windows = os.name == 'nt'
        exe_name = "pg_dump.exe" if is_windows else "pg_dump"

        for bin_dir in dest_path.rglob("bin"):
            if bin_dir.is_dir() and (bin_dir / exe_name).exists():
                return str(bin_dir)

        # Fallback: first bin directory (even if pg_dump check failed,
        # let validate_installation be the authoritative check).
        for bin_dir in dest_path.rglob("bin"):
            if bin_dir.is_dir():
                return str(bin_dir)

        return None
    except Exception as e:
        print(f"PostgreSQL extraction failed: {e}")
        return None


def validate_installation(bin_path: str) -> bool:
    """True if `bin_path` contains pg_dump, pg_restore and psql."""
    try:
        bin_dir = Path(bin_path)
        if not bin_dir.exists():
            return False

        if os.name == 'nt':
            required = ['pg_dump.exe', 'pg_restore.exe', 'psql.exe']
        else:
            required = ['pg_dump', 'pg_restore', 'psql']

        return all((bin_dir / name).exists() for name in required)
    except Exception:
        return False


def extract_version_from_path(path: Path) -> Optional[str]:
    """Best-effort version detection from directory name.

    EDB's archive extracts to 'pgsql/' without version. But if the user points
    at e.g. 'C:/Program Files/PostgreSQL/16/bin', we can read the parent
    folder name ('16') or the version-labelled custom install dir.
    """
    name = path.name
    # Match X.Y.Z, X.Y or just the major version (common for system installs)
    m = re.search(r'(\d+\.\d+\.\d+)', name)
    if m:
        return m.group(1)
    m = re.search(r'(\d+\.\d+)', name)
    if m:
        return m.group(1)
    m = re.fullmatch(r'(\d+)', name)
    if m:
        return m.group(1)

    # pg_config --version would be more reliable but we'd need to exec the
    # binary — keep this function pure for now.
    return None


def _common_system_install_paths() -> List[Path]:
    """System-wide PG install paths to scan on top of the tool's default_dir."""
    paths: List[Path] = []

    if os.name == 'nt':
        pf = os.environ.get('ProgramFiles', r'C:\Program Files')
        root = Path(pf) / 'PostgreSQL'
        if root.exists():
            # e.g. C:\Program Files\PostgreSQL\16\bin, \15\bin, ...
            for sub in root.iterdir():
                if sub.is_dir():
                    bin_dir = sub / 'bin'
                    if bin_dir.exists():
                        paths.append(bin_dir)
    else:
        # Common Linux/macOS locations
        for p in ['/usr/bin', '/usr/local/bin', '/opt/homebrew/bin', '/opt/local/bin']:
            paths.append(Path(p))

    return paths


def detect_installed_versions() -> List[Dict[str, Any]]:
    """Detect installed PostgreSQL client binaries.

    Sources:
      1. DB_CLONE_POSTGRES_BIN env var (Docker/production override)
      2. System-wide PG installs (`C:\\Program Files\\PostgreSQL\\*\\bin`)
      3. Tool-managed default directory from previous downloads
    """
    installed: List[Dict[str, Any]] = []

    # 1) Environment-pinned install (Docker)
    env_bin = os.environ.get('DB_CLONE_POSTGRES_BIN', '')
    if env_bin and Path(env_bin).exists() and validate_installation(env_bin):
        version = (
            os.environ.get('DB_CLONE_POSTGRES_VERSION')
            or extract_version_from_path(Path(env_bin).parent)
            or 'pre-installed'
        )
        installed.append({
            'version': version,
            'bin_path': env_bin,
            'is_valid': True,
            'install_path': str(Path(env_bin).parent),
        })

    # 2) System-wide installs
    for bin_dir in _common_system_install_paths():
        try:
            if not validate_installation(str(bin_dir)):
                continue
            version = extract_version_from_path(bin_dir.parent) or 'system'
            installed.append({
                'version': version,
                'bin_path': str(bin_dir),
                'is_valid': True,
                'install_path': str(bin_dir.parent),
            })
        except Exception:
            continue

    # 3) Tool-managed default directory
    try:
        from src.db_clone_tool.config import get_default_postgres_dir
        default_dir = get_default_postgres_dir()
        if default_dir.exists():
            for item in default_dir.iterdir():
                if not item.is_dir() or item.name == 'downloads':
                    continue
                # Look for bin dir (often ./pgsql/bin because of EDB zip layout)
                for bin_dir in item.rglob('bin'):
                    if bin_dir.is_dir() and validate_installation(str(bin_dir)):
                        version = extract_version_from_path(item) or 'unknown'
                        installed.append({
                            'version': version,
                            'bin_path': str(bin_dir),
                            'is_valid': True,
                            'install_path': str(item),
                        })
                        break
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error scanning default postgres dir: {e}")

    # Deduplicate by bin_path
    seen = set()
    unique: List[Dict[str, Any]] = []
    for inst in installed:
        if inst['bin_path'] in seen:
            continue
        seen.add(inst['bin_path'])
        unique.append(inst)

    # Sort: valid versions newest-first, then the rest
    def sort_key(x):
        v = x.get('version', '')
        try:
            return tuple(int(p) for p in v.split('.'))
        except (ValueError, AttributeError):
            return (0,)

    unique.sort(key=sort_key, reverse=True)
    return unique
