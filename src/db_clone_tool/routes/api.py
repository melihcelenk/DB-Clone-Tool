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
from src.db_clone_tool import storage, config
from src.db_clone_tool.db_manager import DatabaseManager

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
    extract_mysql
)

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__, url_prefix='/api')


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
        
        connection_id = storage.add_connection(data)
        return jsonify({"success": True, "connection_id": connection_id})
    except Exception as e:
        logger.error(f"Error adding connection: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route('/connections/test', methods=['POST'])
def test_connection():
    """Test a connection"""
    try:
        import pymysql
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['host', 'port', 'user', 'password']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "error": f"Missing required field: {field}"
                }), 400
        
        # Test connection directly
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
            
            # Test query
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            conn.close()
            return jsonify({
                "success": True,
                "message": "Connection successful"
            })
        except pymysql.Error as e:
            return jsonify({
                "success": False,
                "error": f"Connection failed: {str(e)}"
            }), 200  # Return 200 but with success: false
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Connection failed: {str(e)}"
            }), 200
        
    except Exception as e:
        logger.error(f"Error testing connection: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


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
    """Get schemas for a connection"""
    try:
        db_manager = DatabaseManager(connection_id)
        schemas = db_manager.get_schemas()
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
    """Get MySQL bin path configuration"""
    try:
        path = config.get_mysql_bin_path()
        return jsonify({"path": path})
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


@api_bp.route('/import/dump', methods=['POST'])
def import_dump():
    """Import SQL dump file to a schema"""
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "error": "No file provided"
            }), 400
        
        file = request.files['file']
        connection_id = request.form.get('connection_id')
        target_schema = request.form.get('target_schema')
        
        if not connection_id or not target_schema:
            return jsonify({
                "success": False,
                "error": "Missing connection_id or target_schema"
            }), 400
        
        if file.filename == '':
            return jsonify({
                "success": False,
                "error": "No file selected"
            }), 400
        
        # Get connection info
        connection_info = storage.get_connection(connection_id)
        if not connection_info:
            return jsonify({
                "success": False,
                "error": "Connection not found"
            }), 404
        
        # Save uploaded file temporarily
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f"import_{uuid.uuid4()}.sql")
        file.save(temp_file)
        
        try:
            # Get mysql path
            mysql_path = config.get_mysql_path()
            if not mysql_path or not os.path.exists(mysql_path):
                raise Exception(f"mysql not found at: {mysql_path}")
            
            # Check if target schema exists, create if not
            db_manager = DatabaseManager(connection_id)
            try:
                db_manager.connect()
                if not db_manager.schema_exists(target_schema):
                    db_manager.create_schema(target_schema)
            finally:
                db_manager.disconnect()
            
            # Build mysql import command
            mysql_cmd = [
                mysql_path,
                '-h', connection_info['host'],
                '-P', str(connection_info.get('port', 3306)),
                '-u', connection_info['user'],
                f'-p{connection_info["password"]}',
                target_schema
            ]
            
            # Execute mysql import
            with open(temp_file, 'r', encoding='utf-8') as f:
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
            
            # Cleanup temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)
            
            return jsonify({
                "success": True,
                "message": f"Dump imported successfully to schema '{target_schema}'"
            })
            
        except Exception as e:
            # Cleanup temp file on error
            if os.path.exists(temp_file):
                os.remove(temp_file)
            raise
            
    except Exception as e:
        logger.error(f"Error importing dump: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route('/export/dump', methods=['POST'])
def export_dump():
    """Export schema to SQL dump file"""
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
        
        # Get connection info
        connection_info = storage.get_connection(connection_id)
        if not connection_info:
            return jsonify({
                "success": False,
                "error": "Connection not found"
            }), 404
        
        # Get mysqldump path
        mysqldump_path = config.get_mysqldump_path()
        if not mysqldump_path or not os.path.exists(mysqldump_path):
            return jsonify({
                "success": False,
                "error": f"mysqldump not found at: {mysqldump_path}"
            }), 400
        
        # Determine output file path
        if export_path:
            # Use provided path
            if not export_path.endswith('.sql'):
                export_path += '.sql'
            output_file = export_path
        else:
            # Use default location: tmp/exports in project directory
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
            backup_dir = BASE_DIR / 'tmp' / 'exports'
            os.makedirs(backup_dir, exist_ok=True)
            output_file = str(backup_dir / f"{source_schema}-{timestamp}-dump.sql")
        
        # Build mysqldump command
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
            '--no-create-db',  # Don't include CREATE DATABASE
            source_schema
        ]
        
        # Execute mysqldump
        with open(output_file, 'w', encoding='utf-8') as f:
            process = subprocess.Popen(
                mysqldump_cmd,
                stdout=f,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.path.dirname(mysqldump_path)
            )
            
            _, stderr = process.communicate()
            
            if process.returncode != 0:
                # Cleanup failed file
                if os.path.exists(output_file):
                    os.remove(output_file)
                raise Exception(f"mysqldump failed: {stderr}")
        
        file_size = os.path.getsize(output_file)
        
        return jsonify({
            "success": True,
            "message": f"Dump exported successfully",
            "file_path": output_file,
            "file_size": file_size
        })
        
    except Exception as e:
        logger.error(f"Error exporting dump: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# MySQL Download Endpoints

@api_bp.route('/mysql/versions', methods=['GET'])
def get_mysql_versions():
    """Get available MySQL versions"""
    try:
        versions = fetch_versions()
        return jsonify({
            "versions": versions,
            "recommended": "8.0.40"
        })
    except Exception as e:
        logger.error(f"Error getting MySQL versions: {e}")
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


@api_bp.route('/mysql/download', methods=['POST'])
def download_mysql_api():
    """Download and install MySQL"""
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
            # Default: tmp/mysql in project directory
            dest_dir = BASE_DIR / 'tmp' / 'mysql'

        # Ensure destination directory exists
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            logger.error(f"Permission denied creating directory {dest_dir}: {e}")
            return jsonify({
                "success": False,
                "error": f"Permission denied: Cannot create directory '{dest_dir}'. Please choose a different location (e.g., C:/mysql or C:/Users/YourName/mysql) or run the application as administrator."
            }), 403
        except OSError as e:
            logger.error(f"OS error creating directory {dest_dir}: {e}")
            return jsonify({
                "success": False,
                "error": f"Cannot create directory '{dest_dir}': {str(e)}. Please choose a different location."
            }), 400

        # Download MySQL
        logger.info(f"Downloading MySQL {version} to {dest_dir}")
        download_dir = dest_dir / 'downloads'
        try:
            download_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            logger.error(f"Permission denied creating download directory {download_dir}: {e}")
            return jsonify({
                "success": False,
                "error": f"Permission denied: Cannot create directory '{download_dir}'. Please choose a different location (e.g., C:/mysql or C:/Users/YourName/mysql) or run the application as administrator."
            }), 403
        except OSError as e:
            logger.error(f"OS error creating download directory {download_dir}: {e}")
            return jsonify({
                "success": False,
                "error": f"Cannot create directory '{download_dir}': {str(e)}. Please choose a different location."
            }), 400

        zip_path = download_mysql(version, str(download_dir))

        if not zip_path:
            return jsonify({
                "success": False,
                "error": "Failed to download MySQL. Please check your internet connection and try again."
            }), 500

        # Extract MySQL
        logger.info(f"Extracting MySQL to {dest_dir}")
        bin_path = extract_mysql(zip_path, str(dest_dir))

        if not bin_path:
            return jsonify({
                "success": False,
                "error": "Failed to extract MySQL archive. The downloaded file may be corrupted."
            }), 500

        # Validate installation
        if not validate_installation(bin_path):
            return jsonify({
                "success": False,
                "error": "MySQL installation validation failed. Required executables not found."
            }), 500

        # Clean up downloaded ZIP
        try:
            os.remove(zip_path)
        except Exception:
            pass  # Ignore cleanup errors

        logger.info(f"MySQL {version} installed successfully at {bin_path}")

        return jsonify({
            "success": True,
            "bin_path": bin_path,
            "version": version,
            "message": f"MySQL {version} installed successfully"
        })

    except Exception as e:
        logger.error(f"Error downloading MySQL: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
