# API Documentation

Complete API reference for DB Clone Tool.

## Base URL

All API endpoints are prefixed with `/api`:

```
http://localhost:5000/api
```

## Authentication

Currently, the API does not require authentication. For production use, implement authentication.

## Endpoints

### Connections

#### List Connections
```http
GET /api/connections
```

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Production DB",
    "host": "192.168.1.100",
    "port": 3306,
    "user": "root",
    "database": "mydb"
  }
]
```

#### Add Connection
```http
POST /api/connections
Content-Type: application/json

{
  "name": "Production DB",
  "host": "192.168.1.100",
  "port": 3306,
  "user": "root",
  "password": "password",
  "database": "mydb"
}
```

**Response:**
```json
{
  "success": true,
  "connection_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Missing required field: host"
}
```

#### Test Connection
```http
POST /api/connections/test
Content-Type: application/json

{
  "host": "192.168.1.100",
  "port": 3306,
  "user": "root",
  "password": "password",
  "database": "mydb"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Connection successful"
}
```

#### Delete Connection
```http
DELETE /api/connections/{connection_id}
```

**Response:**
```json
{
  "success": true
}
```

### Schemas

#### List Schemas
```http
GET /api/schemas/{connection_id}
```

**Response:**
```json
[
  {
    "name": "schema_name",
    "table_count": 10,
    "size_mb": 125.50
  }
]
```

**Error Response:**
```json
{
  "error": "Connection not found"
}
```

### Clone Operations

#### Start Clone Job
```http
POST /api/clone
Content-Type: application/json

{
  "connection_id": "550e8400-e29b-41d4-a716-446655440000",
  "source_schema": "original_schema",
  "target_schema": "backup_schema"
}
```

**Response:**
```json
{
  "success": true,
  "job_id": "660e8400-e29b-41d4-a716-446655440001"
}
```

#### Get Clone Status
```http
GET /api/clone/status/{job_id}
```

**Response:**
```json
{
  "job_id": "660e8400-e29b-41d4-a716-446655440001",
  "connection_id": "550e8400-e29b-41d4-a716-446655440000",
  "source_schema": "original_schema",
  "target_schema": "backup_schema",
  "status": "running",
  "progress": 50,
  "error_message": null,
  "start_time": "2024-01-01T12:00:00",
  "end_time": null
}
```

**Status Values:**
- `pending` - Job created but not started
- `running` - Job is currently running
- `completed` - Job completed successfully
- `failed` - Job failed with error
- `cancelled` - Job was cancelled

#### Get Clone Logs
```http
GET /api/clone/logs/{job_id}
```

**Response:**
```json
[
  "[2024-01-01 12:00:00] [INFO] Starting clone: original_schema -> backup_schema",
  "[2024-01-01 12:00:05] [INFO] Step 1/3: Creating database dump...",
  "[2024-01-01 12:00:10] [INFO] Dump created successfully: 5242880 bytes"
]
```

#### Cancel Clone Job
```http
POST /api/clone/cancel/{job_id}
```

**Response:**
```json
{
  "success": true
}
```

### Configuration

#### Get MySQL Bin Path
```http
GET /api/config/mysql-bin
```

**Response:**
```json
{
  "path": "/usr/bin"
}
```

#### Set MySQL Bin Path
```http
POST /api/config/mysql-bin
Content-Type: application/json

{
  "path": "/usr/bin"
}
```

**Response:**
```json
{
  "success": true
}
```

## Error Responses

All error responses follow this format:

```json
{
  "error": "Error message description"
}
```

Or for operations that return success status:

```json
{
  "success": false,
  "error": "Error message description"
}
```

## HTTP Status Codes

- `200 OK` - Request successful
- `400 Bad Request` - Invalid request data
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

## Rate Limiting

Currently, there is no rate limiting. For production use, implement rate limiting.

## Examples

### Python Example

```python
import requests

BASE_URL = "http://localhost:5000/api"

# Add connection
response = requests.post(f"{BASE_URL}/connections", json={
    "name": "Production DB",
    "host": "192.168.1.100",
    "port": 3306,
    "user": "root",
    "password": "password",
    "database": "mydb"
})
connection_id = response.json()["connection_id"]

# List schemas
response = requests.get(f"{BASE_URL}/schemas/{connection_id}")
schemas = response.json()

# Clone schema
response = requests.post(f"{BASE_URL}/clone", json={
    "connection_id": connection_id,
    "source_schema": "original_schema",
    "target_schema": "backup_schema"
})
job_id = response.json()["job_id"]

# Poll status
import time
while True:
    response = requests.get(f"{BASE_URL}/clone/status/{job_id}")
    status = response.json()
    print(f"Progress: {status['progress']}%")
    
    if status["status"] in ["completed", "failed", "cancelled"]:
        break
    
    time.sleep(1)
```

### cURL Example

```bash
# Add connection
curl -X POST http://localhost:5000/api/connections \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production DB",
    "host": "192.168.1.100",
    "port": 3306,
    "user": "root",
    "password": "password",
    "database": "mydb"
  }'

# List schemas
curl http://localhost:5000/api/schemas/{connection_id}

# Clone schema
curl -X POST http://localhost:5000/api/clone \
  -H "Content-Type: application/json" \
  -d '{
    "connection_id": "{connection_id}",
    "source_schema": "original_schema",
    "target_schema": "backup_schema"
  }'
```
