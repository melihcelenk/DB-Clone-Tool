"""
Unit tests for PostgresManager (DBC-3).

These tests use mocks for psycopg — no live Postgres server required.
Integration tests against a real server can be added separately.
"""
import pytest
from unittest.mock import patch, MagicMock
from src.db_clone_tool import storage


@pytest.fixture
def pg_connection(temp_config_dir):
    """Register a PostgreSQL connection in storage and return its id."""
    conn = {
        'name': 'Local PG',
        'db_type': 'postgres',
        'host': 'localhost',
        'port': 5432,
        'user': 'postgres',
        'password': 'postgres',
        'database': 'hstroke_local',
    }
    return storage.add_connection(conn)


def test_postgres_manager_raises_when_connection_missing(temp_config_dir):
    from src.db_clone_tool.postgres_manager import PostgresManager
    with pytest.raises(ValueError, match="not found"):
        PostgresManager("non-existent-id")


def test_postgres_manager_builds_conninfo(pg_connection):
    from src.db_clone_tool.postgres_manager import PostgresManager
    mgr = PostgresManager(pg_connection)
    info = mgr._build_conninfo()
    # Assertions on substrings — order isn't important for psycopg
    assert 'host=localhost' in info
    assert 'port=5432' in info
    assert 'user=postgres' in info
    assert 'dbname=hstroke_local' in info


def test_postgres_manager_conninfo_overrides_dbname(pg_connection):
    from src.db_clone_tool.postgres_manager import PostgresManager
    mgr = PostgresManager(pg_connection)
    info = mgr._build_conninfo(dbname="postgres")
    assert 'dbname=postgres' in info
    # Original DB in storage shouldn't leak through
    assert 'dbname=hstroke_local' not in info


def test_postgres_manager_conninfo_defaults_to_postgres_db_when_none(temp_config_dir):
    """If connection has no 'database' field, conninfo targets 'postgres' maintenance DB."""
    from src.db_clone_tool.postgres_manager import PostgresManager
    conn_id = storage.add_connection({
        'name': 'PG no db',
        'db_type': 'postgres',
        'host': '1.2.3.4',
        'port': 5432,
        'user': 'u',
        'password': 'p',
    })
    mgr = PostgresManager(conn_id)
    info = mgr._build_conninfo()
    assert 'dbname=postgres' in info


def test_factory_routes_to_postgres_manager(pg_connection):
    from src.db_clone_tool.db_manager_factory import get_database_manager
    from src.db_clone_tool.postgres_manager import PostgresManager
    mgr = get_database_manager(pg_connection)
    assert isinstance(mgr, PostgresManager)


def test_factory_routes_to_mysql_manager_by_default(temp_config_dir):
    """Legacy connections without db_type default to MySQL."""
    from src.db_clone_tool.db_manager_factory import get_database_manager
    from src.db_clone_tool.db_manager import DatabaseManager
    conn_id = storage.add_connection({
        'name': 'Legacy', 'host': 'x', 'port': 3306,
        'user': 'u', 'password': 'p',
    })
    mgr = get_database_manager(conn_id)
    assert isinstance(mgr, DatabaseManager)


def test_factory_rejects_unknown_db_type(temp_config_dir):
    from src.db_clone_tool.db_manager_factory import get_database_manager
    conn_id = storage.add_connection({
        'name': 'X', 'db_type': 'oracle', 'host': 'x', 'port': 1521,
        'user': 'u', 'password': 'p',
    })
    with pytest.raises(ValueError, match="Unsupported db_type"):
        get_database_manager(conn_id)


def test_postgres_test_connection_success(pg_connection):
    """Mock a successful psycopg.connect and SELECT 1."""
    from src.db_clone_tool.postgres_manager import PostgresManager

    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (1,)
    mock_cursor_ctx = MagicMock()
    mock_cursor_ctx.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor_ctx.__exit__ = MagicMock(return_value=False)

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor_ctx
    mock_conn.close = MagicMock()

    with patch('src.db_clone_tool.postgres_manager.psycopg.connect', return_value=mock_conn):
        mgr = PostgresManager(pg_connection)
        ok, msg = mgr.test_connection()
    assert ok is True
    assert 'successful' in msg.lower()


def test_postgres_test_connection_failure(pg_connection):
    from src.db_clone_tool.postgres_manager import PostgresManager

    with patch(
        'src.db_clone_tool.postgres_manager.psycopg.connect',
        side_effect=Exception("FATAL: password authentication failed"),
    ):
        mgr = PostgresManager(pg_connection)
        ok, msg = mgr.test_connection()
    assert ok is False
    assert 'Connection failed' in msg
