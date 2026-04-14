"""
PostgreSQL database connection and schema management.

Mirrors the API of DatabaseManager (mysql) so the rest of the codebase can
switch engines via the factory without caring about the driver.

"Schema" in this tool maps to a PostgreSQL **database**, not a namespace.
PostgreSQL also has in-database schemas (public, etc.), but for the clone tool
the user-facing unit is the database — same conceptual level as a MySQL schema.
"""
import psycopg
from psycopg import sql
from typing import List, Dict, Tuple
from src.db_clone_tool.storage import get_connection


# PostgreSQL built-in / template databases we hide from the user
_SYSTEM_DATABASES = {"postgres", "template0", "template1"}


class PostgresManager:
    """Manages PostgreSQL connections and database operations."""

    def __init__(self, connection_id: str):
        self.connection_id = connection_id
        self.connection_info = get_connection(connection_id)
        if not self.connection_info:
            raise ValueError(f"Connection {connection_id} not found")
        self.conn: psycopg.Connection | None = None

    def _build_conninfo(self, dbname: str | None = None) -> str:
        """Build a psycopg conninfo string.

        If dbname is given, override connection_info's database. When listing
        databases we must connect to a known DB (e.g. 'postgres') because a
        PG connection always targets a specific DB.
        """
        info = self.connection_info
        target_db = dbname or info.get("database") or "postgres"
        return (
            f"host={info['host']} "
            f"port={int(info.get('port', 5432))} "
            f"user={info['user']} "
            f"password={info['password']} "
            f"dbname={target_db} "
            f"connect_timeout=5"
        )

    def connect(self, dbname: str | None = None) -> bool:
        try:
            self.conn = psycopg.connect(self._build_conninfo(dbname))
            # autocommit lets us run CREATE DATABASE / DROP DATABASE
            self.conn.autocommit = True
            return True
        except Exception as e:
            self.conn = None
            raise Exception(f"Connection failed: {str(e)}")

    def disconnect(self):
        if self.conn:
            try:
                self.conn.close()
            finally:
                self.conn = None

    def test_connection(self) -> Tuple[bool, str]:
        try:
            self.connect()
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
            return True, "Connection successful"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
        finally:
            self.disconnect()

    def get_schemas(self) -> List[Dict]:
        """List user databases with table counts and sizes.

        Connects to the default 'postgres' maintenance DB to enumerate DBs,
        then opens a short-lived connection to each to count tables and
        measure on-disk size via pg_database_size().
        """
        self.connect(dbname="postgres")
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT datname
                    FROM pg_database
                    WHERE datistemplate = false
                    ORDER BY datname
                    """
                )
                all_dbs = [row[0] for row in cur.fetchall()]
                user_dbs = [d for d in all_dbs if d not in _SYSTEM_DATABASES]

            result: List[Dict] = []
            for db_name in user_dbs:
                table_count = 0
                size_mb = 0.0

                # Size from the maintenance connection (pg_database_size works from any DB)
                try:
                    with self.conn.cursor() as cur:
                        cur.execute("SELECT pg_database_size(%s)", (db_name,))
                        size_bytes = cur.fetchone()[0] or 0
                        size_mb = round(size_bytes / 1024 / 1024, 2)
                except Exception:
                    size_mb = 0.0

                # Table count requires connecting to that specific database
                try:
                    target_conn = psycopg.connect(self._build_conninfo(dbname=db_name))
                    try:
                        with target_conn.cursor() as cur:
                            cur.execute(
                                """
                                SELECT COUNT(*)
                                FROM information_schema.tables
                                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                                  AND table_type = 'BASE TABLE'
                                """
                            )
                            table_count = cur.fetchone()[0] or 0
                    finally:
                        target_conn.close()
                except Exception:
                    # If we can't connect (e.g. permission), skip counting — better
                    # than failing the whole listing.
                    table_count = 0

                result.append(
                    {
                        "name": db_name,
                        "table_count": int(table_count),
                        "size_mb": float(size_mb),
                    }
                )

            return result
        except Exception as e:
            raise Exception(f"Failed to get schemas: {str(e)}")
        finally:
            self.disconnect()

    def schema_exists(self, schema_name: str) -> bool:
        """Check whether a database named schema_name exists."""
        self.connect(dbname="postgres")
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s", (schema_name,)
                )
                return cur.fetchone() is not None
        except Exception:
            return False
        finally:
            self.disconnect()

    def create_schema(self, schema_name: str) -> bool:
        """Create a new empty database.

        Uses psycopg.sql.Identifier to safely quote the DB name and avoid
        injection.
        """
        self.connect(dbname="postgres")
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    sql.SQL("CREATE DATABASE {} WITH ENCODING 'UTF8'").format(
                        sql.Identifier(schema_name)
                    )
                )
            return True
        except Exception as e:
            raise Exception(f"Failed to create schema: {str(e)}")
        finally:
            self.disconnect()

    def drop_schema(self, schema_name: str) -> bool:
        """Drop the given database. Required by the clone workflow when the
        target already exists.

        Active connections to the target DB will block the DROP; we terminate
        them first (similar to how DataGrip/pgAdmin do it).
        """
        self.connect(dbname="postgres")
        try:
            with self.conn.cursor() as cur:
                # Kick out any open backends on the target DB
                cur.execute(
                    """
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = %s AND pid <> pg_backend_pid()
                    """,
                    (schema_name,),
                )
                cur.execute(
                    sql.SQL("DROP DATABASE IF EXISTS {}").format(
                        sql.Identifier(schema_name)
                    )
                )
            return True
        except Exception as e:
            raise Exception(f"Failed to drop schema: {str(e)}")
        finally:
            self.disconnect()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
