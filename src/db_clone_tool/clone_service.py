"""
Schema cloning service using mysqldump
"""
import os
import subprocess
import threading
import uuid
import tempfile
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
from src.db_clone_tool.config import get_mysqldump_path, get_mysql_path
from src.db_clone_tool.storage import get_connection
from src.db_clone_tool.db_manager import DatabaseManager


# Global job storage (in-memory)
_jobs: Dict[str, Dict] = {}
_jobs_lock = threading.Lock()


class CloneJob:
    """Represents a schema cloning job"""
    
    def __init__(self, connection_id: str, source_schema: str, target_schema: str):
        self.job_id = str(uuid.uuid4())
        self.connection_id = connection_id
        self.source_schema = source_schema
        self.target_schema = target_schema
        self.status = 'pending'  # pending, running, completed, failed, cancelled
        self.progress = 0
        self.logs = []
        self.error_message = None
        self.start_time = None
        self.end_time = None
        self.process = None
        
        # Store job
        with _jobs_lock:
            _jobs[self.job_id] = {
                'job_id': self.job_id,
                'connection_id': connection_id,
                'source_schema': source_schema,
                'target_schema': target_schema,
                'status': self.status,
                'progress': self.progress,
                'logs': self.logs,
                'error_message': self.error_message,
                'start_time': self.start_time,
                'end_time': self.end_time
            }
    
    def _add_log(self, message: str, level: str = 'info'):
        """Add a log message"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{level.upper()}] {message}"
        self.logs.append(log_entry)
        
        # Update in global storage
        with _jobs_lock:
            if self.job_id in _jobs:
                _jobs[self.job_id]['logs'] = self.logs.copy()
    
    def _update_status(self, status: str, progress: int = None, error: str = None):
        """Update job status"""
        self.status = status
        if progress is not None:
            self.progress = progress
        if error:
            self.error_message = error
        
        # Update in global storage
        with _jobs_lock:
            if self.job_id in _jobs:
                _jobs[self.job_id]['status'] = status
                if progress is not None:
                    _jobs[self.job_id]['progress'] = progress
                if error:
                    _jobs[self.job_id]['error_message'] = error
    
    def run(self):
        """Execute the cloning process"""
        self._update_status('running', progress=0)
        self.start_time = datetime.now()
        
        with _jobs_lock:
            if self.job_id in _jobs:
                _jobs[self.job_id]['start_time'] = self.start_time
        
        try:
            # Get connection info
            connection_info = get_connection(self.connection_id)
            if not connection_info:
                raise Exception(f"Connection {self.connection_id} not found")
            
            self._add_log(f"Starting clone: {self.source_schema} -> {self.target_schema}")
            self._add_log(f"Host: {connection_info['host']}:{connection_info.get('port', 3306)}")
            
            # Get mysqldump and mysql paths
            mysqldump_path = get_mysqldump_path()
            mysql_path = get_mysql_path()
            
            if not mysqldump_path or not os.path.exists(mysqldump_path):
                raise Exception(f"mysqldump not found at: {mysqldump_path}")
            
            if not mysql_path or not os.path.exists(mysql_path):
                raise Exception(f"mysql not found at: {mysql_path}")
            
            self._add_log(f"Using mysqldump: {mysqldump_path}")
            self._add_log(f"Using mysql: {mysql_path}")
            
            # Note: Target schema creation will be handled in Step 2
            # We don't drop it here to avoid any issues
            
            # Create temporary dump file
            temp_dir = tempfile.gettempdir()
            dump_file = os.path.join(temp_dir, f"clone_{self.job_id}.sql")
            
            self._add_log("Step 1/3: Creating database dump...")
            self._update_status('running', progress=20)
            
            # Build mysqldump command
            # CRITICAL: Use --no-create-db to avoid DROP/CREATE DATABASE in dump
            # This prevents any risk of modifying the source database
            # We'll create the target database separately
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
                '--no-create-db',  # CRITICAL: Don't include CREATE/DROP DATABASE statements
                self.source_schema  # Just the schema name, NOT --databases flag
            ]
            
            # Execute mysqldump
            try:
                with open(dump_file, 'w', encoding='utf-8') as f:
                    self.process = subprocess.Popen(
                        mysqldump_cmd,
                        stdout=f,
                        stderr=subprocess.PIPE,
                        text=True,
                        cwd=os.path.dirname(mysqldump_path)
                    )
                    
                    # Wait for completion and capture stderr
                    _, stderr = self.process.communicate()
                    
                    if self.process.returncode != 0:
                        raise Exception(f"mysqldump failed: {stderr}")
                
                self._add_log(f"Dump created successfully: {os.path.getsize(dump_file)} bytes")
            except Exception as e:
                if os.path.exists(dump_file):
                    os.remove(dump_file)
                raise Exception(f"Failed to create dump: {str(e)}")
            
            self._add_log("Step 2/3: Creating target database and modifying dump file...")
            self._update_status('running', progress=50)
            
            # Create target database first (separate from dump)
            db_manager = DatabaseManager(self.connection_id)
            try:
                db_manager.connect()
                
                # Drop target if exists
                if db_manager.schema_exists(self.target_schema):
                    self._add_log(f"Target schema '{self.target_schema}' exists, dropping it...")
                    with db_manager.conn.cursor() as cursor:
                        cursor.execute(f"DROP DATABASE `{self.target_schema}`")
                        db_manager.conn.commit()
                    self._add_log(f"Dropped existing target schema '{self.target_schema}'")
                
                # Create new target database
                self._add_log(f"Creating target schema '{self.target_schema}'...")
                db_manager.create_schema(self.target_schema)
                self._add_log(f"Target schema '{self.target_schema}' created")
            finally:
                db_manager.disconnect()
            
            # Modify dump file to use target schema name
            # CRITICAL: With --no-create-db, dump only contains:
            # - USE source_schema; (we'll replace this)
            # - CREATE TABLE, INSERT, etc. (no schema.table references)
            # We ONLY replace USE statements - nothing else touches the source schema
            try:
                with open(dump_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # CRITICAL: Only replace USE statements - this is safe
                # Replace any USE source_schema with USE target_schema
                content = content.replace(
                    f"USE `{self.source_schema}`",
                    f"USE `{self.target_schema}`"
                )
                content = content.replace(
                    f"USE {self.source_schema}",  # Without backticks
                    f"USE {self.target_schema}"
                )
                
                # Prepend USE statement if not present (some dumps might not have it)
                if f"USE `{self.target_schema}`" not in content and f"USE {self.target_schema}" not in content:
                    content = f"USE `{self.target_schema}`;\n\n" + content
                
                with open(dump_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self._add_log("Dump file modified for target schema (only USE statements changed)")
            except Exception as e:
                if os.path.exists(dump_file):
                    os.remove(dump_file)
                raise Exception(f"Failed to modify dump file: {str(e)}")
            
            self._add_log("Step 3/3: Importing dump to target schema...")
            self._update_status('running', progress=75)
            
            # Build mysql import command
            mysql_cmd = [
                mysql_path,
                '-h', connection_info['host'],
                '-P', str(connection_info.get('port', 3306)),
                '-u', connection_info['user'],
                f'-p{connection_info["password"]}'
            ]
            
            # Execute mysql import
            try:
                with open(dump_file, 'r', encoding='utf-8') as f:
                    self.process = subprocess.Popen(
                        mysql_cmd,
                        stdin=f,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        cwd=os.path.dirname(mysql_path)
                    )
                    
                    _, stderr = self.process.communicate()
                    
                    if self.process.returncode != 0:
                        raise Exception(f"mysql import failed: {stderr}")
                
                self._add_log("Import completed successfully")
            except Exception as e:
                if os.path.exists(dump_file):
                    os.remove(dump_file)
                raise Exception(f"Failed to import dump: {str(e)}")
            
            # Cleanup dump file
            if os.path.exists(dump_file):
                os.remove(dump_file)
                self._add_log("Temporary dump file removed")
            
            self._add_log(f"Clone completed successfully: {self.source_schema} -> {self.target_schema}")
            self._update_status('completed', progress=100)
            self.end_time = datetime.now()
            
            with _jobs_lock:
                if self.job_id in _jobs:
                    _jobs[self.job_id]['end_time'] = self.end_time
            
        except Exception as e:
            self._add_log(f"Error: {str(e)}", level='error')
            self._update_status('failed', progress=self.progress, error=str(e))
            self.end_time = datetime.now()
            
            with _jobs_lock:
                if self.job_id in _jobs:
                    _jobs[self.job_id]['end_time'] = self.end_time
    
    def cancel(self):
        """Cancel the running job"""
        if self.status == 'running' and self.process:
            try:
                self.process.terminate()
                self._add_log("Job cancelled by user")
                self._update_status('cancelled')
            except Exception:
                pass


def start_clone_job(connection_id: str, source_schema: str, target_schema: str) -> str:
    """
    Start a new clone job in background thread
    
    Args:
        connection_id: ID of the database connection
        source_schema: Source schema name
        target_schema: Target schema name
        
    Returns:
        Job ID
    """
    job = CloneJob(connection_id, source_schema, target_schema)
    
    # Run in background thread
    thread = threading.Thread(target=job.run, daemon=True)
    thread.start()
    
    return job.job_id


def get_job_status(job_id: str) -> Optional[Dict]:
    """Get status of a clone job"""
    with _jobs_lock:
        return _jobs.get(job_id)


def get_job_logs(job_id: str) -> list:
    """Get logs for a clone job"""
    with _jobs_lock:
        if job_id in _jobs:
            return _jobs[job_id].get('logs', [])
    return []


def cancel_job(job_id: str) -> bool:
    """Cancel a running job"""
    with _jobs_lock:
        if job_id in _jobs:
            job_data = _jobs[job_id]
            if job_data['status'] == 'running':
                # Create a temporary job object to call cancel
                job = CloneJob(job_data['connection_id'], job_data['source_schema'], job_data['target_schema'])
                job.job_id = job_id
                job.status = job_data['status']
                job.process = None  # We don't have the actual process reference
                job.cancel()
                return True
    return False
