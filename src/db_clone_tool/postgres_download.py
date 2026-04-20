"""
PostgreSQL client binaries downloader (DBC-3).

Mirrors mysql_download.py for the Postgres side. Two sources depending on OS:

  - Windows: EnterpriseDB's public zip bundle
    (`postgresql-{version}-{build}-windows-x64-binaries.zip`).
  - Linux (amd64, Debian-family): PGDG APT archive `.deb` for
    `postgresql-client-{major}`. Same minor versions catalogued for Windows
    are available under apt-archive.postgresql.org.

The "bin path" produced by this module is the directory containing pg_dump,
pg_restore and psql — same shape as MySQL's `bin/`.
"""
import io
import os
import re
import tarfile
import zipfile
import requests
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any


def _pgdg_linux_url(version: str) -> str:
    """PGDG APT archive URL for the `postgresql-client-{major}` .deb.

    Pool layout is stable across releases; archive keeps every historic minor.
    We target Debian bookworm (pgdg120+1) because that matches python:3.11-slim
    which is the runtime base image we ship.
    """
    major = version.split('.')[0]
    return (
        f"https://apt-archive.postgresql.org/pub/repos/apt/pool/main/"
        f"p/postgresql-{major}/postgresql-client-{major}_{version}-1.pgdg120+1_amd64.deb"
    )


# EDB keeps older builds online under stable URLs. Each entry pins the
# last known-good Windows build. If EDB ever bumps the -N suffix and
# invalidates the URL, the download fails cleanly and the user falls back
# to the "Manual Path" option (same UX as MySQL).
#
# PGDG apt-archive only mirrors older releases. Versions not yet archived
# on Linux use None — the download UI will show them as Windows-only and
# direct Linux/Docker users to rebuild the image instead.
# Source: https://www.enterprisedb.com/download-postgresql-binaries
POSTGRES_VERSIONS: Dict[str, Dict[str, Optional[str]]] = {
    "17.8":  {"windows": "https://get.enterprisedb.com/postgresql/postgresql-17.8-1-windows-x64-binaries.zip",  "linux": None},
    "17.5":  {"windows": "https://get.enterprisedb.com/postgresql/postgresql-17.5-1-windows-x64-binaries.zip",  "linux": _pgdg_linux_url("17.5")},
    "17.4":  {"windows": "https://get.enterprisedb.com/postgresql/postgresql-17.4-1-windows-x64-binaries.zip",  "linux": _pgdg_linux_url("17.4")},
    "17.2":  {"windows": "https://get.enterprisedb.com/postgresql/postgresql-17.2-1-windows-x64-binaries.zip",  "linux": _pgdg_linux_url("17.2")},
    "17.0":  {"windows": "https://get.enterprisedb.com/postgresql/postgresql-17.0-1-windows-x64-binaries.zip",  "linux": _pgdg_linux_url("17.0")},
    "16.8":  {"windows": "https://get.enterprisedb.com/postgresql/postgresql-16.8-1-windows-x64-binaries.zip",  "linux": None},
    "16.6":  {"windows": "https://get.enterprisedb.com/postgresql/postgresql-16.6-1-windows-x64-binaries.zip",  "linux": _pgdg_linux_url("16.6")},
    "16.4":  {"windows": "https://get.enterprisedb.com/postgresql/postgresql-16.4-1-windows-x64-binaries.zip",  "linux": _pgdg_linux_url("16.4")},
    "15.10": {"windows": "https://get.enterprisedb.com/postgresql/postgresql-15.10-1-windows-x64-binaries.zip", "linux": _pgdg_linux_url("15.10")},
    "14.15": {"windows": "https://get.enterprisedb.com/postgresql/postgresql-14.15-1-windows-x64-binaries.zip", "linux": _pgdg_linux_url("14.15")},
    "13.18": {"windows": "https://get.enterprisedb.com/postgresql/postgresql-13.18-1-windows-x64-binaries.zip", "linux": _pgdg_linux_url("13.18")},
}

RECOMMENDED_VERSION = "17.8"  # Latest stable release.


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
    # Linux: PGDG archive .deb. macOS has no equivalent wired up.
    import sys
    if sys.platform.startswith('linux'):
        return entry.get('linux')
    return None


def is_download_supported() -> bool:
    """True if we can auto-download on the current OS.

    Windows uses EDB zip bundles; Linux uses PGDG .deb archive.
    macOS is left to the user (brew install postgresql).
    """
    import sys
    return os.name == 'nt' or sys.platform.startswith('linux')


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

        # Filename follows the URL's extension so extract_postgres() can
        # dispatch on it (.zip on Windows, .deb on Linux).
        ext = '.deb' if url.endswith('.deb') else '.zip'
        filename = f"postgresql-{version}{ext}"
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


def _extract_deb(deb_path: Path, dest_dir: Path) -> None:
    """Extract a Debian .deb (ar archive) into dest_dir.

    `.deb` is an `ar` archive holding three members: debian-binary, control.tar.*
    and data.tar.*. We only care about data.tar.* — the payload that would
    land under / on a real install. We skip dpkg entirely (not present in
    python:3.11-slim) and parse the ar header ourselves — the format is tiny:
    8-byte magic + 60-byte headers per member, padded to an even boundary.
    """
    with open(deb_path, 'rb') as f:
        magic = f.read(8)
        if magic != b'!<arch>\n':
            raise ValueError(f"Not an ar archive: {deb_path}")
        while True:
            header = f.read(60)
            if len(header) < 60:
                break
            name = header[:16].decode('ascii', errors='replace').strip()
            size_field = header[48:58].decode('ascii', errors='replace').strip()
            size = int(size_field)
            content = f.read(size)
            if size % 2:  # ar pads odd-sized members with a trailing newline
                f.read(1)
            if name.startswith('data.tar'):
                if name.endswith('.xz'):
                    mode = 'r:xz'
                elif name.endswith('.gz'):
                    mode = 'r:gz'
                elif name.endswith('.zst') or name.endswith('.zstd'):
                    # Py 3.11 tarfile can't read zstd natively; PGDG still ships xz
                    # but guard the case anyway.
                    raise ValueError("zstd-compressed .deb not supported")
                else:
                    mode = 'r:*'
                with tarfile.open(fileobj=io.BytesIO(content), mode=mode) as tar:
                    tar.extractall(dest_dir)
                return
    raise ValueError("data.tar.* not found in .deb archive")


def extract_postgres(archive_path: str, dest_dir: str) -> Optional[str]:
    """Extract a Postgres archive and return the path to its bin/ directory.

    Windows: EDB zip — top-level `pgsql/` with `bin/`, `lib/`, etc.
    Linux:   PGDG .deb — payload mirrors filesystem paths, so pg_dump lands
             at `{dest_dir}/usr/lib/postgresql/{major}/bin/pg_dump`.
    We search recursively for a bin directory that contains pg_dump in both
    cases — same strategy as MySQL's archive extraction.
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
        elif archive_path.endswith('.deb'):
            _extract_deb(archive_file, dest_path)
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
