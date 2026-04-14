"""
Factory for database managers.

Routes to MySQL or PostgreSQL implementation based on the stored connection's
`db_type` field. Connections created before DBC-3 don't have this field —
they default to "mysql" so existing setups keep working without migration.
"""
from typing import Union
from src.db_clone_tool.storage import get_connection
from src.db_clone_tool.db_manager import DatabaseManager
from src.db_clone_tool.postgres_manager import PostgresManager


DB_TYPE_MYSQL = "mysql"
DB_TYPE_POSTGRES = "postgres"
SUPPORTED_DB_TYPES = (DB_TYPE_MYSQL, DB_TYPE_POSTGRES)

DEFAULT_PORTS = {
    DB_TYPE_MYSQL: 3306,
    DB_TYPE_POSTGRES: 5432,
}


def get_db_type(connection_info: dict) -> str:
    """Return db_type of a connection dict, defaulting to 'mysql' for legacy entries."""
    return (connection_info.get("db_type") or DB_TYPE_MYSQL).lower()


def get_database_manager(connection_id: str) -> Union[DatabaseManager, PostgresManager]:
    """Return the correct manager instance for the stored connection.

    Raises ValueError if the connection is not found or has an unknown db_type.
    """
    info = get_connection(connection_id)
    if not info:
        raise ValueError(f"Connection {connection_id} not found")

    db_type = get_db_type(info)
    if db_type == DB_TYPE_MYSQL:
        return DatabaseManager(connection_id)
    if db_type == DB_TYPE_POSTGRES:
        return PostgresManager(connection_id)

    raise ValueError(
        f"Unsupported db_type '{db_type}' for connection {connection_id}. "
        f"Expected one of: {SUPPORTED_DB_TYPES}"
    )
