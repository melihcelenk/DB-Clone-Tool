"""
API routes for DB Clone Tool
"""
from flask import Blueprint, jsonify, request
from pathlib import Path
import logging
import uuid
import os
import subprocess
import tempfile
import threading
from src.db_clone_tool import storage, config, APP_NAME
from src.db_clone_tool.db_manager import DatabaseManager
from src.db_clone_tool.postgres_manager import PostgresManager
from src.db_clone_tool.db_manager_factory import (
    get_database_manager,
    get_db_type,
    DB_TYPE_MYSQL,
    DB_TYPE_POSTGRES,
    SUPPORTED_DB_TYPES,
    DEFAULT_PORTS,
)

# Base directory
BASE_DIR = Path(__file__).parent.parent.parent.parent
from src.db_clone_tool.clone_service import (
    start_clone_job,
    get_job_status,
    get_job_logs,
    cancel_job
)
from src.db_clone_tool.mysql_download import (
    fetch_versions,
    validate_installation,
    download_mysql,
    extract_mysql,
    detect_installed_versions
)
from src.db_clone_tool import postgres_download as pgdl

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Track download progress for background jobs
_download_jobs = {}
_pg_download_jobs = {}


@api_bp.route('/connections', methods=['GET'])
def get_connections():
    """Get all saved connections"""
    try:
        connections = storage.load_connections()
        return jsonify(connections)
    except Exception as e:
        logger.error(f"Error getting connections: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route('/connections', methods=['POST'])
def add_connection():
    """Add a new connection"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['name', 'host', 'port', 'user', 'password']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "error": f"Missing required field: {field}"
                }), 400

        # db_type is optional — defaults to 'mysql' for backward compat.
        # If provided, validate it.
        db_type = (data.get('db_type') or DB_TYPE_MYSQL).lower()
        if db_type not in SUPPORTED_DB_TYPES:
            return jsonify({
                "success": False,
                "error": f"Unsupported db_type '{db_type}'. Use one of: {SUPPORTED_DB_TYPES}"
            }), 400
        data['db_type'] = db_type

        connection_id = storage.add_connection(data)
        return jsonify({"success": True, "connection_id": connection_id})
    except Exception as e:
        logger.error(f"Error adding connection: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route('/connections/test', methods=['POST'])
def test_connection():
    """Test a connection — routes by db_type (defaults to mysql)."""
    try:
        data = request.get_json()

        required_fields = ['host', 'port', 'user', 'password']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "error": f"Missing required field: {field}"
                }), 400

        db_type = (data.get('db_type') or DB_TYPE_MYSQL).lower()
        if db_type not in SUPPORTED_DB_TYPES:
            return jsonify({
                "success": False,
                "error": f"Unsupported db_type '{db_type}'"
            }), 400

        if db_type == DB_TYPE_POSTGRES:
            return _test_postgres_connection(data)
        return _test_mysql_connection(data)
    except Exception as e:
        logger.error(f"Error testing connection: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def _test_mysql_connection(data):
    """MySQL connection test — extracted so test_connection can dispatch."""
    import pymysql
    try:
        conn = pymysql.connect(
            host=data['host'],
            port=int(data.get('port', 3306)),
            user=data['user'],
            password=data['password'],
            database=data.get('database', ''),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=5
        )
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        conn.close()
        return jsonify({"success": True, "message": "Connection successful"})
    except pymysql.Error as e:
        return jsonify({"success": False, "error": f"Connection failed: {str(e)}"}), 200
    except Exception as e:
        return jsonify({"success": False, "error": f"Connection failed: {str(e)}"}), 200


def _test_postgres_connection(data):
    """PostgreSQL connection test using psycopg."""
    import psycopg
    # PG always connects to a specific DB — use provided one, else 'postgres'
    # maintenance DB (guaranteed to exist).
    target_db = data.get('database') or 'postgres'
    conninfo = (
        f"host={data['host']} "
        f"port={int(data.get('port', 5432))} "
        f"user={data['user']} "
        f"password={data['password']} "
        f"dbname={target_db} "
        f"connect_timeout=5"
    )
    try:
        with psycopg.connect(conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return jsonify({"success": True, "message": "Connection successful"})
    except psycopg.Error as e:
        return jsonify({"success": False, "error": f"Connection failed: {str(e)}"}), 200
    except Exception as e:
        return jsonify({"success": False, "error": f"Connection failed: {str(e)}"}), 200


@api_bp.route('/connections/<connection_id>', methods=['GET'])
def get_connection(connection_id):
    """Get a specific connection"""
    try:
        conn = storage.get_connection(connection_id)
        if not conn:
            return jsonify({"error": "Connection not found"}), 404
        return jsonify(conn)
    except Exception as e:
        logger.error(f"Error getting connection: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route('/connections/<connection_id>', methods=['PUT'])
def update_connection(connection_id):
    """Update a connection"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['name', 'host', 'port', 'user', 'password']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "error": f"Missing required field: {field}"
                }), 400

        # Validate db_type if provided (keeps existing value otherwise)
        if 'db_type' in data:
            db_type = (data.get('db_type') or DB_TYPE_MYSQL).lower()
            if db_type not in SUPPORTED_DB_TYPES:
                return jsonify({
                    "success": False,
                    "error": f"Unsupported db_type '{db_type}'. Use one of: {SUPPORTED_DB_TYPES}"
                }), 400
            data['db_type'] = db_type

        success = storage.update_connection(connection_id, data)
        if not success:
            return jsonify({"success": False, "error": "Connection not found"}), 404
        
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error updating connection: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route('/connections/<connection_id>', methods=['DELETE'])
def delete_connection(connection_id):
    """Delete a connection"""
    try:
        success = storage.delete_connection(connection_id)
        return jsonify({"success": success})
    except Exception as e:
        logger.error(f"Error deleting connection: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route('/schemas/<connection_id>', methods=['GET'])
def get_schemas(connection_id):
    """Get schemas for a connection (MySQL databases or Postgres databases)."""
    try:
        db_manager = get_database_manager(connection_id)
        try:
            schemas = db_manager.get_schemas()
        finally:
            db_manager.disconnect()
        return jsonify(schemas)
    except Exception as e:
        logger.error(f"Error getting schemas: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route('/clone', methods=['POST'])
def clone_schema():
    """Start a clone job"""
    try:
        data = request.get_json()
        
        required_fields = ['connection_id', 'source_schema', 'target_schema']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "error": f"Missing required field: {field}"
                }), 400
        
        job_id = start_clone_job(
            data['connection_id'],
            data['source_schema'],
            data['target_schema']
        )
        
        return jsonify({"success": True, "job_id": job_id})
    except Exception as e:
        logger.error(f"Error starting clone: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route('/clone/status/<job_id>', methods=['GET'])
def get_clone_status(job_id):
    """Get status of a clone job"""
    try:
        job_status = get_job_status(job_id)
        if not job_status:
            return jsonify({"error": "Job not found"}), 404
        
        return jsonify(job_status)
    except Exception as e:
        logger.error(f"Error getting clone status: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route('/clone/logs/<job_id>', methods=['GET'])
def get_clone_logs(job_id):
    """Get logs for a clone job"""
    try:
        logs = get_job_logs(job_id)
        return jsonify(logs)
    except Exception as e:
        logger.error(f"Error getting clone logs: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route('/clone/cancel/<job_id>', methods=['POST'])
def cancel_clone_job(job_id):
    """Cancel a clone job"""
    try:
        success = cancel_job(job_id)
        return jsonify({"success": success})
    except Exception as e:
        logger.error(f"Error cancelling clone: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route('/config/mysql-bin', methods=['GET'])
def get_mysql_bin_config():
    """Get MySQL bin path + matching version, so the Configuration panel
    can show which MySQL is in use (path alone is opaque)."""
    try:
        path = config.get_mysql_bin_path()
        version = None
        if path:
            for inst in detect_installed_versions():
                if inst.get('bin_path') == path:
                    version = inst.get('version')
                    break
        return jsonify({"path": path, "version": version})
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route('/config/mysql-bin', methods=['POST'])
def set_mysql_bin_config():
    """Set MySQL bin path configuration"""
    try:
        data = request.get_json()

        if 'path' not in data:
            return jsonify({
                "success": False,
                "error": "Missing 'path' field"
            }), 400

        config.set_mysql_bin_path(data['path'])
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error setting config: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route('/config/postgres-bin', methods=['GET'])
def get_postgres_bin_config():
    """Get PostgreSQL bin path configuration + the matching version, so the
    main Configuration panel can show which PG the user is actually using
    (path alone doesn't tell them)."""
    try:
        path = config.get_postgres_bin_path()
        version = None
        if path:
            for inst in pgdl.detect_installed_versions():
                if inst.get('bin_path') == path:
                    version = inst.get('version')
                    break
        return jsonify({"path": path, "version": version})
    except Exception as e:
        logger.error(f"Error getting postgres config: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route('/config/postgres-bin', methods=['POST'])
def set_postgres_bin_config():
    """Set PostgreSQL bin path configuration (must contain pg_dump/pg_restore/psql)."""
    try:
        data = request.get_json()

        if 'path' not in data:
            return jsonify({
                "success": False,
                "error": "Missing 'path' field"
            }), 400

        is_valid, err = config.validate_postgres_bin_path(data['path'])
        if not is_valid:
            return jsonify({"success": False, "error": err}), 400

        config.set_postgres_bin_path(data['path'])
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error setting postgres config: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route('/import/dump', methods=['POST'])
def import_dump():
    """Import SQL dump file to a schema (MySQL or PostgreSQL based on connection's db_type)."""
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400

        file = request.files['file']
        connection_id = request.form.get('connection_id')
        target_schema = request.form.get('target_schema')

        if not connection_id or not target_schema:
            return jsonify({"success": False, "error": "Missing connection_id or target_schema"}), 400
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400

        connection_info = storage.get_connection(connection_id)
        if not connection_info:
            return jsonify({"success": False, "error": "Connection not found"}), 404

        db_type = get_db_type(connection_info)

        # Save uploaded file temporarily — keep original extension so pg_restore
        # can detect format when we hand it the path.
        import tempfile
        temp_dir = tempfile.gettempdir()
        ext = Path(file.filename).suffix or '.sql'
        temp_file = os.path.join(temp_dir, f"import_{uuid.uuid4()}{ext}")
        file.save(temp_file)

        try:
            if db_type == DB_TYPE_POSTGRES:
                _import_postgres_dump(connection_info, connection_id, target_schema, temp_file)
            else:
                _import_mysql_dump(connection_info, connection_id, target_schema, temp_file)

            return jsonify({
                "success": True,
                "message": f"Dump imported successfully to schema '{target_schema}'"
            })
        finally:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
    except Exception as e:
        logger.error(f"Error importing dump: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def _import_mysql_dump(connection_info, connection_id, target_schema, dump_path):
    if _looks_like_postgres_dump(dump_path):
        raise Exception(
            "This file appears to be a PostgreSQL dump. MySQL cannot import "
            "PostgreSQL dumps directly — syntax differs (double quotes vs backticks, "
            "data types, SERIAL vs AUTO_INCREMENT, etc.). Export the source data from "
            "a MySQL connection instead, or use a dedicated PostgreSQL→MySQL migration tool."
        )

    mysql_path = config.get_mysql_path()
    if not mysql_path or not os.path.exists(mysql_path):
        raise Exception(f"mysql not found at: {mysql_path}")

    db_manager = DatabaseManager(connection_id)
    try:
        db_manager.connect()
        if not db_manager.schema_exists(target_schema):
            db_manager.create_schema(target_schema)
    finally:
        db_manager.disconnect()

    mysql_cmd = [
        mysql_path,
        '-h', connection_info['host'],
        '-P', str(connection_info.get('port', 3306)),
        '-u', connection_info['user'],
        f'-p{connection_info["password"]}',
        target_schema
    ]
    with open(dump_path, 'r', encoding='utf-8') as f:
        process = subprocess.Popen(
            mysql_cmd,
            stdin=f,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.path.dirname(mysql_path)
        )
        _, stderr = process.communicate()
        if process.returncode != 0:
            raise Exception(f"mysql import failed: {stderr}")


def _import_postgres_dump(connection_info, connection_id, target_schema, dump_path):
    """Import a Postgres dump into target DB.

    Format selection:
      - .backup / .dump / binary-detected → pg_restore
      - .sql / plain text → psql
    """
    # Fail fast on cross-engine imports — MySQL dumps use backtick identifier
    # quoting (`foo`), Postgres uses double quotes ("foo"). Handing a MySQL
    # dump to psql only produces opaque syntax errors.
    if _looks_like_mysql_dump(dump_path):
        raise Exception(
            "This file appears to be a MySQL dump (contains MySQL-specific syntax like "
            "backtick-quoted identifiers or 'ENGINE=InnoDB'). PostgreSQL cannot import "
            "MySQL dumps directly — syntax differs (backticks vs double quotes, data "
            "types, auto-increment, etc.). Export the source data from a PostgreSQL "
            "connection instead, or use a dedicated MySQL→PostgreSQL migration tool."
        )

    # Ensure target DB exists
    pg_mgr = PostgresManager(connection_id)
    if not pg_mgr.schema_exists(target_schema):
        pg_mgr.create_schema(target_schema)

    env = os.environ.copy()
    env['PGPASSWORD'] = connection_info['password']

    host = connection_info['host']
    port = str(connection_info.get('port', 5432))
    user = connection_info['user']

    # Decide format: prefer pg_restore for custom/directory/tar formats (magic bytes PGDMP)
    is_custom = _is_pg_custom_format(dump_path)

    if is_custom:
        pg_restore_path = config.get_pg_restore_path()
        if not pg_restore_path or not os.path.exists(pg_restore_path):
            raise Exception(f"pg_restore not found at: {pg_restore_path}")
        cmd = [
            pg_restore_path,
            '-h', host, '-p', port, '-U', user,
            '-d', target_schema,
            '--no-owner', '--no-privileges',
            dump_path,
        ]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, env=env, cwd=os.path.dirname(pg_restore_path))
        _, stderr = process.communicate()
        if process.returncode != 0 and 'ERROR:' in (stderr or ''):
            raise Exception(f"pg_restore failed: {stderr}")
    else:
        psql_path = config.get_psql_path()
        if not psql_path or not os.path.exists(psql_path):
            raise Exception(f"psql not found at: {psql_path}")
        cmd = [
            psql_path,
            '-h', host, '-p', port, '-U', user,
            '-d', target_schema,
            '-v', 'ON_ERROR_STOP=1',
            '-f', dump_path,
        ]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, env=env, cwd=os.path.dirname(psql_path))
        _, stderr = process.communicate()
        if process.returncode != 0:
            raise Exception(f"psql import failed: {stderr}")


def _is_pg_custom_format(path) -> bool:
    """Detect pg_dump custom format by magic header 'PGDMP'."""
    try:
        with open(path, 'rb') as f:
            return f.read(5) == b'PGDMP'
    except Exception:
        return False


def _looks_like_mysql_dump(path) -> bool:
    """Heuristic: does the file look like a MySQL dump?

    MySQL dumps use backtick-quoted identifiers (``CREATE TABLE `foo` ...``);
    PostgreSQL dumps use double quotes (``CREATE TABLE "foo" ...``). Backticks
    never appear in valid PostgreSQL DDL, so their presence is a strong signal.
    """
    import re
    try:
        with open(path, 'rb') as f:
            if f.read(5) == b'PGDMP':
                return False  # PG custom format — definitely not MySQL
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            sample = f.read(16384)  # first 16 KB is plenty
        # Backtick around an identifier — unambiguous MySQL marker
        if re.search(r'`[A-Za-z_][A-Za-z_0-9]*`', sample):
            return True
        if '-- MySQL dump' in sample or 'ENGINE=InnoDB' in sample or 'AUTO_INCREMENT' in sample:
            return True
        return False
    except Exception:
        return False


def _looks_like_postgres_dump(path) -> bool:
    """Heuristic for the inverse case: PG dump being imported into MySQL.

    pg_dump plain SQL uses double-quoted identifiers, `SET client_encoding`,
    `CREATE EXTENSION`, schema-qualified names (`public.table`), and is
    emitted by `pg_dump`. Any one of these is enough in a plain-text dump.
    """
    try:
        with open(path, 'rb') as f:
            if f.read(5) == b'PGDMP':
                return True  # custom-format — definitely Postgres
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            sample = f.read(16384)
        markers = [
            '-- PostgreSQL database dump',
            'SET client_encoding',
            'SET standard_conforming_strings',
            'CREATE EXTENSION',
            'pg_catalog.',
            'WITH (OIDS',
        ]
        return any(m in sample for m in markers)
    except Exception:
        return False


@api_bp.route('/export/dump', methods=['POST'])
def export_dump():
    """Export schema to dump file (MySQL SQL or Postgres custom format based on db_type)."""
    try:
        data = request.get_json()

        connection_id = data.get('connection_id')
        source_schema = data.get('source_schema')
        export_path = data.get('export_path', '').strip()

        if not connection_id or not source_schema:
            return jsonify({
                "success": False,
                "error": "Missing connection_id or source_schema"
            }), 400

        connection_info = storage.get_connection(connection_id)
        if not connection_info:
            return jsonify({"success": False, "error": "Connection not found"}), 404

        db_type = get_db_type(connection_info)

        if db_type == DB_TYPE_POSTGRES:
            return _export_postgres_dump(connection_info, source_schema, export_path)
        return _export_mysql_dump(connection_info, source_schema, export_path)
    except Exception as e:
        logger.error(f"Error exporting dump: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def _export_mysql_dump(connection_info, source_schema, export_path):
    mysqldump_path = config.get_mysqldump_path()
    if not mysqldump_path or not os.path.exists(mysqldump_path):
        return jsonify({"success": False, "error": f"mysqldump not found at: {mysqldump_path}"}), 400

    if export_path:
        if not export_path.endswith('.sql'):
            export_path += '.sql'
        output_file = export_path
    else:
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
        backup_dir = BASE_DIR / 'tmp' / 'exports'
        os.makedirs(backup_dir, exist_ok=True)
        output_file = str(backup_dir / f"{source_schema}-{timestamp}-dump.sql")

    mysqldump_cmd = [
        mysqldump_path,
        '-h', connection_info['host'],
        '-P', str(connection_info.get('port', 3306)),
        '-u', connection_info['user'],
        f'-p{connection_info["password"]}',
        '--single-transaction',
        '--routines',
        '--triggers',
        '--events',
        '--no-create-db',
        source_schema
    ]

    with open(output_file, 'w', encoding='utf-8') as f:
        process = subprocess.Popen(
            mysqldump_cmd,
            stdout=f, stderr=subprocess.PIPE,
            text=True, cwd=os.path.dirname(mysqldump_path)
        )
        _, stderr = process.communicate()
        if process.returncode != 0:
            if os.path.exists(output_file):
                os.remove(output_file)
            raise Exception(f"mysqldump failed: {stderr}")

    file_size = os.path.getsize(output_file)
    return jsonify({
        "success": True,
        "message": "Dump exported successfully",
        "file_path": output_file,
        "file_size": file_size
    })


def _export_postgres_dump(connection_info, source_schema, export_path):
    """Export PG database using pg_dump.

    Default format: custom (-Fc, .backup) — compressed, reliable, pg_restore-ready.
    If user provides an export path ending with .sql, we switch to plain SQL format
    (-Fp) so the extension matches the content.
    """
    pg_dump_path = config.get_pg_dump_path()
    if not pg_dump_path or not os.path.exists(pg_dump_path):
        return jsonify({
            "success": False,
            "error": f"pg_dump not found at: {pg_dump_path}. Configure PostgreSQL bin path in Settings."
        }), 400

    # Decide format from extension
    use_plain_sql = bool(export_path and export_path.lower().endswith('.sql'))

    if export_path:
        # Ensure a sensible extension
        if use_plain_sql:
            output_file = export_path
        else:
            if not export_path.lower().endswith(('.backup', '.dump')):
                export_path += '.backup'
            output_file = export_path
    else:
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
        backup_dir = BASE_DIR / 'tmp' / 'exports'
        os.makedirs(backup_dir, exist_ok=True)
        output_file = str(backup_dir / f"{source_schema}-{timestamp}-dump.backup")

    env = os.environ.copy()
    env['PGPASSWORD'] = connection_info['password']

    fmt_flag = '-Fp' if use_plain_sql else '-Fc'
    cmd = [
        pg_dump_path,
        '-h', connection_info['host'],
        '-p', str(connection_info.get('port', 5432)),
        '-U', connection_info['user'],
        fmt_flag,
        '--no-owner',
        '--no-privileges',
        '-f', output_file,
        '-d', source_schema,
    ]

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd=os.path.dirname(pg_dump_path),
    )
    _, stderr = process.communicate()
    if process.returncode != 0:
        if os.path.exists(output_file):
            os.remove(output_file)
        raise Exception(f"pg_dump failed: {stderr}")

    file_size = os.path.getsize(output_file)
    return jsonify({
        "success": True,
        "message": "Dump exported successfully",
        "file_path": output_file,
        "file_size": file_size,
        "format": "plain" if use_plain_sql else "custom"
    })


# MySQL Download Endpoints

@api_bp.route('/mysql/versions', methods=['GET'])
def get_mysql_versions():
    """Get available MySQL versions with installed status"""
    try:
        versions = fetch_versions()
        installed = detect_installed_versions()
        
        # Create a map of installed versions by version string
        installed_map = {inst['version']: inst for inst in installed}
        
        # Build version list with installed status
        versions_with_status = []
        for version in versions:
            version_info = {
                'version': version,
                'recommended': version == "8.0.40",
                'installed': False,
                'bin_path': None,
                'is_valid': None,
                'install_path': None
            }
            
            # Check if this version is installed
            if version in installed_map:
                inst_info = installed_map[version]
                version_info['installed'] = True
                version_info['bin_path'] = inst_info['bin_path']
                version_info['is_valid'] = inst_info['is_valid']
                version_info['install_path'] = inst_info['install_path']
            
            versions_with_status.append(version_info)
        
        return jsonify({
            "versions": versions_with_status,
            "recommended": "8.0.40"
        })
    except Exception as e:
        logger.error(f"Error getting MySQL versions: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route('/mysql/installed', methods=['GET'])
def get_installed_mysql_versions():
    """Get list of installed MySQL versions"""
    try:
        installed = detect_installed_versions()
        return jsonify({"installed": installed})
    except Exception as e:
        logger.error(f"Error getting installed MySQL versions: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route('/mysql/validate', methods=['POST'])
def validate_mysql_path():
    """Validate MySQL installation path"""
    try:
        data = request.get_json()

        if not data or 'path' not in data:
            return jsonify({
                "success": False,
                "error": "Missing 'path' field"
            }), 400

        bin_path = data['path']
        is_valid = validate_installation(bin_path)

        if is_valid:
            return jsonify({
                "valid": True,
                "path": bin_path
            })
        else:
            return jsonify({
                "valid": False,
                "error": "MySQL executables not found in specified path"
            })

    except Exception as e:
        logger.error(f"Error validating MySQL path: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Docker and monitoring"""
    return jsonify({
        "status": "healthy",
        "service": APP_NAME,
        "version": "1.0.0"
    }), 200


@api_bp.route('/mysql/default-directory', methods=['GET'])
def get_default_mysql_directory():
    """Get the default MySQL installation directory path"""
    try:
        from src.db_clone_tool.config import get_default_mysql_dir
        default_dir = get_default_mysql_dir()
        return jsonify({
            "path": str(default_dir),
            "platform": "windows" if os.name == 'nt' else "unix"
        })
    except Exception as e:
        logger.error(f"Error getting default directory: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route('/mysql/use', methods=['POST'])
def use_mysql_version():
    """Use an existing MySQL installation"""
    try:
        data = request.get_json()
        bin_path = data.get('bin_path')
        
        if not bin_path:
            return jsonify({
                "success": False,
                "error": "Missing 'bin_path' field"
            }), 400
        
        # Validate the path
        is_valid = validate_installation(bin_path)
        if not is_valid:
            return jsonify({
                "success": False,
                "error": "Invalid MySQL installation. Required executables not found."
            }), 400
        
        # Save to config
        from src.db_clone_tool.config import set_mysql_bin_path
        set_mysql_bin_path(bin_path)
        
        logger.info(f"MySQL bin path set to: {bin_path}")
        
        return jsonify({
            "success": True,
            "bin_path": bin_path,
            "message": "MySQL installation configured successfully"
        })
        
    except Exception as e:
        logger.error(f"Error using MySQL version: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route('/mysql/repair', methods=['POST'])
def repair_mysql_version():
    """Repair a MySQL installation by re-extracting if needed"""
    try:
        data = request.get_json()
        version = data.get('version')
        install_path = data.get('install_path')
        
        if not version:
            return jsonify({
                "success": False,
                "error": "Missing 'version' field"
            }), 400
        
        if not install_path:
            return jsonify({
                "success": False,
                "error": "Missing 'install_path' field"
            }), 400
        
        install_dir = Path(install_path)
        if not install_dir.exists():
            return jsonify({
                "success": False,
                "error": f"Installation directory does not exist: {install_path}"
            }), 400
        
        # Check if archive exists in downloads folder
        from src.db_clone_tool.config import get_default_mysql_dir
        default_dir = get_default_mysql_dir()
        downloads_dir = default_dir / 'downloads'
        
        is_windows = os.name == 'nt'
        archive_name = f"mysql-{version}.zip" if is_windows else f"mysql-{version}.tar.xz"
        archive_path = downloads_dir / archive_name
        
        if archive_path.exists():
            # Re-extract from existing archive
            logger.info(f"Re-extracting MySQL {version} from existing archive")
            bin_path = extract_mysql(str(archive_path), str(install_dir.parent))
            
            if not bin_path:
                return jsonify({
                    "success": False,
                    "error": "Failed to re-extract MySQL archive"
                }), 500
            
            # Validate after extraction
            if not validate_installation(bin_path):
                return jsonify({
                    "success": False,
                    "error": "Repair failed: Installation is still invalid after re-extraction"
                }), 500
            
            return jsonify({
                "success": True,
                "bin_path": bin_path,
                "message": f"MySQL {version} repaired successfully"
            })
        else:
            # Archive doesn't exist, need to re-download
            return jsonify({
                "success": False,
                "error": f"Archive not found. Please download MySQL {version} again.",
                "requires_download": True
            }), 404
        
    except Exception as e:
        logger.error(f"Error repairing MySQL version: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route('/mysql/download', methods=['POST'])
def download_mysql_api():
    """Start MySQL download as background job, return job_id for progress polling"""
    try:
        data = request.get_json()

        version = data.get('version')
        destination = data.get('destination', '').strip()

        if not version:
            return jsonify({
                "success": False,
                "error": "Missing 'version' field"
            }), 400

        # Determine destination directory
        if destination:
            dest_dir = Path(destination)
        else:
            from src.db_clone_tool.config import get_default_mysql_dir
            dest_dir = get_default_mysql_dir()

        # Ensure destination directory exists with fallback
        from src.db_clone_tool.config import create_directory_with_fallback
        success, created_path, error_msg = create_directory_with_fallback(dest_dir)

        if not success:
            logger.error(f"Failed to create directory: {error_msg}")
            return jsonify({"success": False, "error": error_msg}), 403

        if created_path != dest_dir:
            logger.info(f"Using fallback directory: {created_path}")
            dest_dir = created_path

        download_dir = dest_dir / 'downloads'
        success, created_download_dir, error_msg = create_directory_with_fallback(download_dir)

        if not success:
            logger.error(f"Failed to create download directory: {error_msg}")
            return jsonify({"success": False, "error": error_msg}), 403

        download_dir = created_download_dir

        # Create job and start background download
        job_id = str(uuid.uuid4())
        _download_jobs[job_id] = {
            'status': 'running',
            'phase': 'downloading',
            'percent': 0,
            'error': None,
            'bin_path': None
        }

        def progress_callback(percent):
            _download_jobs[job_id]['percent'] = min(percent, 90)  # Reserve 90-100 for extract+validate

        def run_download():
            try:
                logger.info(f"[{job_id}] Downloading MySQL {version} to {download_dir}")
                zip_path = download_mysql(version, str(download_dir), progress_callback=progress_callback)

                if not zip_path:
                    _download_jobs[job_id].update({
                        'status': 'failed',
                        'error': 'Failed to download MySQL. Please check your internet connection and try again.'
                    })
                    return

                _download_jobs[job_id].update({'phase': 'extracting', 'percent': 92})
                logger.info(f"[{job_id}] Extracting MySQL to {dest_dir}")
                bin_path = extract_mysql(zip_path, str(dest_dir))

                if not bin_path:
                    _download_jobs[job_id].update({
                        'status': 'failed',
                        'error': 'Failed to extract MySQL archive. The downloaded file may be corrupted.'
                    })
                    return

                _download_jobs[job_id].update({'phase': 'validating', 'percent': 96})
                if not validate_installation(bin_path):
                    _download_jobs[job_id].update({
                        'status': 'failed',
                        'error': 'MySQL installation validation failed. Required executables not found.'
                    })
                    return

                try:
                    os.remove(zip_path)
                except Exception:
                    pass

                logger.info(f"[{job_id}] MySQL {version} installed successfully at {bin_path}")
                _download_jobs[job_id].update({
                    'status': 'completed',
                    'phase': 'done',
                    'percent': 100,
                    'bin_path': bin_path
                })

            except Exception as e:
                logger.error(f"[{job_id}] Download error: {e}")
                _download_jobs[job_id].update({
                    'status': 'failed',
                    'error': str(e)
                })

        thread = threading.Thread(target=run_download, daemon=True)
        thread.start()

        return jsonify({"job_id": job_id})

    except Exception as e:
        logger.error(f"Error starting MySQL download: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route('/mysql/download/progress/<job_id>', methods=['GET'])
def download_progress(job_id):
    """Get download progress for a background job"""
    job = _download_jobs.get(job_id)
    if not job:
        return jsonify({"status": "not_found", "percent": 0, "error": "Job not found"}), 404

    return jsonify({
        "status": job['status'],
        "phase": job['phase'],
        "percent": job['percent'],
        "error": job.get('error'),
        "bin_path": job.get('bin_path')
    })


# ---------------------------------------------------------------------------
# PostgreSQL download endpoints — mirrors the MySQL flow (DBC-3)
# ---------------------------------------------------------------------------

@api_bp.route('/postgres/versions', methods=['GET'])
def get_postgres_versions():
    """Available PostgreSQL versions with installed status."""
    try:
        versions = pgdl.fetch_versions()
        installed = pgdl.detect_installed_versions()
        installed_map = {inst['version']: inst for inst in installed}

        versions_with_status = []
        for version in versions:
            info = {
                'version': version,
                'recommended': version == pgdl.RECOMMENDED_VERSION,
                'installed': False,
                'bin_path': None,
                'is_valid': None,
                'install_path': None,
            }
            if version in installed_map:
                inst = installed_map[version]
                info.update({
                    'installed': True,
                    'bin_path': inst['bin_path'],
                    'is_valid': inst['is_valid'],
                    'install_path': inst['install_path'],
                })
            versions_with_status.append(info)

        return jsonify({
            "versions": versions_with_status,
            "recommended": pgdl.RECOMMENDED_VERSION,
            "download_supported": pgdl.is_download_supported(),
        })
    except Exception as e:
        logger.error(f"Error getting PostgreSQL versions: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route('/postgres/installed', methods=['GET'])
def get_installed_postgres_versions():
    """List detected PG installations (env var, Program Files, tool default dir)."""
    try:
        return jsonify({"installed": pgdl.detect_installed_versions()})
    except Exception as e:
        logger.error(f"Error getting installed PG versions: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route('/postgres/validate', methods=['POST'])
def validate_postgres_path():
    """Validate that a path contains pg_dump / pg_restore / psql."""
    try:
        data = request.get_json()
        if not data or 'path' not in data:
            return jsonify({"success": False, "error": "Missing 'path' field"}), 400
        bin_path = data['path']
        if pgdl.validate_installation(bin_path):
            return jsonify({"valid": True, "path": bin_path})
        return jsonify({"valid": False, "error": "PostgreSQL executables (pg_dump/pg_restore/psql) not found in specified path"})
    except Exception as e:
        logger.error(f"Error validating PostgreSQL path: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route('/postgres/default-directory', methods=['GET'])
def get_default_postgres_directory():
    """Default install directory for tool-managed PG downloads."""
    try:
        from src.db_clone_tool.config import get_default_postgres_dir
        default_dir = get_default_postgres_dir()
        return jsonify({
            "path": str(default_dir),
            "platform": "windows" if os.name == 'nt' else "unix",
        })
    except Exception as e:
        logger.error(f"Error getting default postgres directory: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route('/postgres/use', methods=['POST'])
def use_postgres_version():
    """Point the tool at an existing PG install — writes config.json."""
    try:
        data = request.get_json()
        bin_path = data.get('bin_path')
        if not bin_path:
            return jsonify({"success": False, "error": "Missing 'bin_path' field"}), 400
        if not pgdl.validate_installation(bin_path):
            return jsonify({
                "success": False,
                "error": "Invalid PostgreSQL installation. Required executables not found.",
            }), 400
        config.set_postgres_bin_path(bin_path)
        logger.info(f"PostgreSQL bin path set to: {bin_path}")
        return jsonify({
            "success": True,
            "bin_path": bin_path,
            "message": "PostgreSQL installation configured successfully",
        })
    except Exception as e:
        logger.error(f"Error using PostgreSQL version: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route('/postgres/download', methods=['POST'])
def download_postgres_api():
    """Kick off a background download + extract + validate job."""
    try:
        data = request.get_json()
        version = data.get('version')
        destination = data.get('destination', '').strip()

        if not version:
            return jsonify({"success": False, "error": "Missing 'version' field"}), 400

        if not pgdl.is_download_supported():
            return jsonify({
                "success": False,
                "error": (
                    "Auto-download is only supported on Windows. On Linux/macOS, "
                    "install PostgreSQL client tools via your package manager "
                    "(apt install postgresql-client / brew install postgresql) "
                    "and use 'Select Installed Version'."
                ),
            }), 400

        if destination:
            dest_dir = Path(destination)
        else:
            from src.db_clone_tool.config import get_default_postgres_dir
            dest_dir = get_default_postgres_dir()

        from src.db_clone_tool.config import create_directory_with_fallback
        success, created_path, error_msg = create_directory_with_fallback(dest_dir)
        if not success:
            logger.error(f"Failed to create PG directory: {error_msg}")
            return jsonify({"success": False, "error": error_msg}), 403
        if created_path != dest_dir:
            logger.info(f"Using fallback directory: {created_path}")
            dest_dir = created_path

        download_dir = dest_dir / 'downloads'
        success, created_download_dir, error_msg = create_directory_with_fallback(download_dir)
        if not success:
            logger.error(f"Failed to create PG download directory: {error_msg}")
            return jsonify({"success": False, "error": error_msg}), 403
        download_dir = created_download_dir

        # The extracted install lives in a per-version subdirectory so repeated
        # downloads of different versions don't clobber each other.
        install_root = dest_dir / version

        job_id = str(uuid.uuid4())
        _pg_download_jobs[job_id] = {
            'status': 'running',
            'phase': 'downloading',
            'percent': 0,
            'error': None,
            'bin_path': None,
        }

        def progress_callback(percent):
            _pg_download_jobs[job_id]['percent'] = min(percent, 90)

        def run_download():
            try:
                logger.info(f"[{job_id}] Downloading PostgreSQL {version} to {download_dir}")
                zip_path = pgdl.download_postgres(
                    version, str(download_dir), progress_callback=progress_callback
                )
                if not zip_path:
                    _pg_download_jobs[job_id].update({
                        'status': 'failed',
                        'error': 'Failed to download PostgreSQL. Check your internet connection and try again.',
                    })
                    return

                _pg_download_jobs[job_id].update({'phase': 'extracting', 'percent': 92})
                logger.info(f"[{job_id}] Extracting PostgreSQL to {install_root}")
                bin_path = pgdl.extract_postgres(zip_path, str(install_root))
                if not bin_path:
                    _pg_download_jobs[job_id].update({
                        'status': 'failed',
                        'error': 'Failed to extract PostgreSQL archive. The downloaded file may be corrupted.',
                    })
                    return

                _pg_download_jobs[job_id].update({'phase': 'validating', 'percent': 96})
                if not pgdl.validate_installation(bin_path):
                    _pg_download_jobs[job_id].update({
                        'status': 'failed',
                        'error': 'PostgreSQL installation validation failed. Required executables not found.',
                    })
                    return

                try:
                    os.remove(zip_path)
                except Exception:
                    pass

                logger.info(f"[{job_id}] PostgreSQL {version} installed at {bin_path}")
                _pg_download_jobs[job_id].update({
                    'status': 'completed',
                    'phase': 'done',
                    'percent': 100,
                    'bin_path': bin_path,
                })
            except Exception as e:
                logger.error(f"[{job_id}] PG download error: {e}")
                _pg_download_jobs[job_id].update({
                    'status': 'failed',
                    'error': str(e),
                })

        thread = threading.Thread(target=run_download, daemon=True)
        thread.start()
        return jsonify({"job_id": job_id})
    except Exception as e:
        logger.error(f"Error starting PostgreSQL download: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route('/postgres/download/progress/<job_id>', methods=['GET'])
def postgres_download_progress(job_id):
    """Poll the progress of a PG download job."""
    job = _pg_download_jobs.get(job_id)
    if not job:
        return jsonify({"status": "not_found", "percent": 0, "error": "Job not found"}), 404
    return jsonify({
        "status": job['status'],
        "phase": job['phase'],
        "percent": job['percent'],
        "error": job.get('error'),
        "bin_path": job.get('bin_path'),
    })
