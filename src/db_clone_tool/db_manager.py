"""
MySQL database connection and schema management
"""
import pymysql
from typing import List, Dict, Optional, Tuple
from src.db_clone_tool.storage import get_connection


class DatabaseManager:
    """Manages MySQL database connections and operations"""
    
    def __init__(self, connection_id: str):
        """
        Initialize database manager with connection ID
        
        Args:
            connection_id: ID of the saved connection
        """
        self.connection_id = connection_id
        self.connection_info = get_connection(connection_id)
        
        if not self.connection_info:
            raise ValueError(f"Connection {connection_id} not found")
        
        self.conn = None
    
    def connect(self) -> bool:
        """
        Connect to MySQL database
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.conn = pymysql.connect(
                host=self.connection_info['host'],
                port=int(self.connection_info.get('port', 3306)),
                user=self.connection_info['user'],
                password=self.connection_info['password'],
                database=self.connection_info.get('database', ''),
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            return True
        except Exception as e:
            self.conn = None
            raise Exception(f"Connection failed: {str(e)}")
    
    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        Test database connection
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if not self.conn:
                self.connect()
            
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            return True, "Connection successful"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
        finally:
            if self.conn:
                self.disconnect()
    
    def get_schemas(self) -> List[Dict]:
        """
        Get list of all schemas (databases) in MySQL
        
        Returns:
            List of schema dictionaries with name, table_count, and size info
        """
        if not self.conn:
            self.connect()
        
        try:
            with self.conn.cursor() as cursor:
                # Get all databases except system databases
                cursor.execute("""
                    SELECT SCHEMA_NAME as name
                    FROM INFORMATION_SCHEMA.SCHEMATA
                    WHERE SCHEMA_NAME NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys')
                    ORDER BY SCHEMA_NAME
                """)
                schemas = cursor.fetchall()
                
                # Get additional info for each schema
                result = []
                for schema in schemas:
                    schema_name = schema['name']
                    
                    # Get table count
                    cursor.execute("""
                        SELECT COUNT(*) as table_count
                        FROM INFORMATION_SCHEMA.TABLES
                        WHERE TABLE_SCHEMA = %s
                    """, (schema_name,))
                    table_info = cursor.fetchone()
                    table_count = table_info['table_count'] if table_info else 0
                    
                    # Get schema size
                    cursor.execute("""
                        SELECT 
                            ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) as size_mb
                        FROM information_schema.TABLES
                        WHERE TABLE_SCHEMA = %s
                    """, (schema_name,))
                    size_info = cursor.fetchone()
                    size_mb = size_info['size_mb'] if size_info and size_info['size_mb'] else 0
                    
                    result.append({
                        'name': schema_name,
                        'table_count': table_count,
                        'size_mb': float(size_mb) if size_mb else 0.0
                    })
                
                return result
        except Exception as e:
            raise Exception(f"Failed to get schemas: {str(e)}")
    
    def schema_exists(self, schema_name: str) -> bool:
        """
        Check if a schema exists
        
        Args:
            schema_name: Name of the schema to check
            
        Returns:
            True if schema exists, False otherwise
        """
        if not self.conn:
            self.connect()
        
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM INFORMATION_SCHEMA.SCHEMATA
                    WHERE SCHEMA_NAME = %s
                """, (schema_name,))
                result = cursor.fetchone()
                return result['count'] > 0
        except Exception:
            return False
    
    def create_schema(self, schema_name: str) -> bool:
        """
        Create a new empty schema
        
        Args:
            schema_name: Name of the schema to create
            
        Returns:
            True if successful, False otherwise
        """
        if not self.conn:
            self.connect()
        
        try:
            with self.conn.cursor() as cursor:
                # Escape schema name to prevent SQL injection
                cursor.execute(f"CREATE DATABASE `{schema_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                self.conn.commit()
                return True
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            raise Exception(f"Failed to create schema: {str(e)}")
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
