"""
Storage management for database connections
"""
import json
import base64
import uuid
from pathlib import Path
from typing import List, Dict, Optional
from src.db_clone_tool import config as _config


def _encode_password(password: str) -> str:
    """Encode password using base64 (simple obfuscation)"""
    return base64.b64encode(password.encode('utf-8')).decode('utf-8')


def _decode_password(encoded: str) -> str:
    """Decode password from base64"""
    try:
        return base64.b64decode(encoded.encode('utf-8')).decode('utf-8')
    except Exception:
        return encoded


def load_connections() -> List[Dict]:
    """Load all saved connections from file"""
    if not _config.CONNECTIONS_FILE.exists():
        return []
    
    try:
        with open(_config.CONNECTIONS_FILE, 'r', encoding='utf-8') as f:
            connections = json.load(f)
            # Decode passwords
            for conn in connections:
                if 'password' in conn:
                    conn['password'] = _decode_password(conn['password'])
            return connections
    except Exception:
        return []


def save_connections(connections: List[Dict]):
    """Save connections to file"""
    # Encode passwords before saving
    connections_to_save = []
    for conn in connections:
        conn_copy = conn.copy()
        if 'password' in conn_copy:
            conn_copy['password'] = _encode_password(conn_copy['password'])
        connections_to_save.append(conn_copy)
    
    with open(_config.CONNECTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(connections_to_save, f, indent=2)


def add_connection(connection: Dict) -> str:
    """Add a new connection and return its ID"""
    connections = load_connections()
    
    # Generate ID if not provided
    if 'id' not in connection or not connection['id']:
        connection['id'] = str(uuid.uuid4())
    
    connections.append(connection)
    save_connections(connections)
    return connection['id']


def update_connection(connection_id: str, updates: Dict) -> bool:
    """Update an existing connection"""
    connections = load_connections()
    
    for i, conn in enumerate(connections):
        if conn.get('id') == connection_id:
            connections[i].update(updates)
            save_connections(connections)
            return True
    
    return False


def delete_connection(connection_id: str) -> bool:
    """Delete a connection by ID"""
    connections = load_connections()
    
    filtered = [c for c in connections if c.get('id') != connection_id]
    
    if len(filtered) < len(connections):
        save_connections(filtered)
        return True
    
    return False


def get_connection(connection_id: str) -> Optional[Dict]:
    """Get a connection by ID"""
    connections = load_connections()
    
    for conn in connections:
        if conn.get('id') == connection_id:
            return conn
    
    return None
