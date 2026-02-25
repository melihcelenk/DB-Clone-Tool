# Deployment Guide - DB Clone Tool

## Table of Contents
- [Docker Deployment (Recommended)](#docker-deployment-recommended)
- [Native Installation](#native-installation)
- [Platform-Specific Notes](#platform-specific-notes)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

---

## Docker Deployment (Recommended)

### Prerequisites
- Docker 20.10+
- Docker Compose 1.29+

### Quick Start

**Option A - Pull from Docker Hub (fastest):**

```bash
docker run -d \
  -p 5000:5000 \
  -v ./config.local:/app/config.local \
  -v ./tmp:/app/tmp \
  --name db-clone-tool \
  --restart unless-stopped \
  melihcelenk/db-clone-tool:0.2.0
```

**Option B - Build from source:**

```bash
# Clone repository
git clone https://github.com/melihcelenk/db-clone-tool.git
cd db-clone-tool

# Start service
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

**Access the application:**
- Web UI: http://localhost:5000
- Health Check: http://localhost:5000/api/health

### MySQL Binaries

MySQL binaries (mysqldump, mysql) are **pre-installed** in the Docker image at `/app/mysql/bin`. No additional configuration needed.

### Data Persistence

Two volumes are mounted for data persistence:

```yaml
volumes:
  - ./config.local:/app/config.local  # Connection configurations
  - ./tmp:/app/tmp                    # Export files and downloads
```

**Backup your data:**
```bash
tar -czf backup-$(date +%Y%m%d).tar.gz config.local/ tmp/
```

### Environment Variables

Customize deployment via `docker-compose.yml`:

```yaml
environment:
  - DB_CLONE_MYSQL_BIN=/app/mysql/bin      # MySQL binaries location
  - DB_CLONE_CONFIG_DIR=/app/config.local  # Config directory
  - FLASK_ENV=production                   # Flask environment
  - FLASK_DEBUG=0                          # Debug mode (0=off, 1=on)
```

### Container Management

**Start/Stop:**
```bash
docker-compose up -d      # Start in background
docker-compose down       # Stop and remove container
docker-compose restart    # Restart service
```

**Logs:**
```bash
docker-compose logs -f              # Follow logs
docker-compose logs --tail=100      # Last 100 lines
```

**Update:**
```bash
git pull
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Production Deployment

**Security Hardening:**
1. Change default port in `docker-compose.yml`:
   ```yaml
   ports:
     - "8080:5000"  # Use non-standard port
   ```

2. Use reverse proxy (nginx, traefik):
   ```nginx
   location /db-clone-tool/ {
       proxy_pass http://localhost:5000/;
       proxy_set_header Host $host;
   }
   ```

3. Enable HTTPS with Let's Encrypt

**Monitoring:**
```bash
# Health check
curl http://localhost:5000/api/health

# Container health
docker-compose ps
```

---

## Native Installation

### Windows

**Prerequisites:**
- Python 3.8+
- MySQL binaries (optional - can download via app)

**Quick Start:**
1. Double-click `run.bat`
2. Application starts automatically
3. Access http://localhost:5000

**Manual Installation:**
```cmd
# Create virtual environment
python -m venv venv
venv\Scripts\activate.bat

# Install dependencies
pip install -e .

# Run application
python -m src.db_clone_tool.main
```

### Linux / macOS

**Prerequisites:**
- Python 3.8+
- MySQL binaries (optional)

**Quick Start:**
```bash
# Make script executable
chmod +x run.sh

# Run
./run.sh
```

**Manual Installation:**
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e .

# Run application
python -m src.db_clone_tool.main
```

---

## Platform-Specific Notes

### Default MySQL Installation Paths

When downloading MySQL via the application, binaries are saved to:

| Platform | Default Path |
|----------|--------------|
| **Windows** | `%LOCALAPPDATA%\db-clone-tool\mysql\bin` |
| **Linux** | `~/.local/share/db-clone-tool/mysql/bin` |
| **macOS** | `~/.local/share/db-clone-tool/mysql/bin` |
| **Docker** | `/app/mysql/bin` (pre-installed) |

### Permission Fallback

If the default path is not writable, the application automatically falls back to:
- `~/.db-clone-tool/mysql/` (user home directory)

### Archive Format Support

| Platform | Supported Formats |
|----------|-------------------|
| **Windows** | `.zip` |
| **Linux** | `.tar.xz`, `.tar`, `.zip` |
| **macOS** | `.tar.xz`, `.tar`, `.zip` |

---

## Configuration

### MySQL Binaries

**Option 1: Download via Application (Recommended)**
1. Open application
2. Click "Configure" → "MySQL Settings"
3. Click "Download MySQL"
4. Select version (recommended: 8.0.40)
5. Path auto-configured

**Option 2: Manual Configuration**
1. Install MySQL on your system
2. Open application
3. Click "Configure" → "MySQL Settings"
4. Enter path to MySQL bin directory
   - Windows: `C:/Program Files/MySQL/MySQL Server 8.0/bin`
   - Linux: `/usr/bin` or `/usr/local/mysql/bin`
   - macOS: `/usr/local/mysql/bin`

**Option 3: Environment Variable (Docker/Advanced)**
```bash
export DB_CLONE_MYSQL_BIN=/custom/path/to/mysql/bin
```

### Connection Storage

Connections are stored in:
- **Native:** `config.local/connections.json`
- **Docker:** Volume-mounted `./config.local/connections.json`

**Security Note:** Passwords are base64 encoded (basic obfuscation). For production, consider encrypting the entire config directory.

---

## Troubleshooting

### Docker Issues

**Container won't start:**
```bash
# Check logs
docker-compose logs

# Rebuild image
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

**Port already in use:**
```bash
# Change port in docker-compose.yml
ports:
  - "8080:5000"  # Use port 8080
```

**Health check failing:**
```bash
# Check if app is running
docker-compose ps

# Check logs
docker-compose logs db-clone-tool

# Manual health check
docker exec db-clone-tool curl http://localhost:5000/api/health
```

### Native Installation Issues

**mysqldump not found:**
- Configure MySQL bin path in application settings
- Or download MySQL via application

**Permission denied:**
- Application will automatically fallback to `~/.db-clone-tool/`
- Or choose a custom writable location

**Connection failed:**
- Verify MySQL server is running
- Check host, port, username, password
- Ensure user has required permissions

**Python dependencies missing:**
```bash
# Reinstall dependencies
pip install -e . --force-reinstall
```

### Platform-Specific Issues

**Windows: Python not found**
- Install Python from https://python.org
- Ensure "Add Python to PATH" is checked

**Linux: python3-venv not found**
```bash
# Ubuntu/Debian
sudo apt install python3-venv python3-pip

# Fedora/RHEL
sudo dnf install python3-pip

# Arch
sudo pacman -S python-pip
```

**macOS: Command not found**
```bash
# Install Python via Homebrew
brew install python3
```

---

## Performance Tuning

### Docker Resource Limits

```yaml
# docker-compose.yml
services:
  db-clone-tool:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          memory: 512M
```

### Database Connection Pooling

For high-volume usage, configure connection pooling in your MySQL server.

---

## Security Best Practices

1. **Use HTTPS** in production (reverse proxy)
2. **Restrict network access** (firewall rules)
3. **Encrypt connection passwords** (custom encryption)
4. **Regular backups** of `config.local/`
5. **Update regularly** (git pull + rebuild)
6. **Use non-root user** (Docker default: appuser)
7. **Limit container resources** (prevent DoS)

---

## Monitoring and Logging

### Health Checks

**Manual:**
```bash
curl http://localhost:5000/api/health
```

**Automated (cron):**
```bash
*/5 * * * * curl -f http://localhost:5000/api/health || systemctl restart db-clone-tool
```

### Logs

**Docker:**
```bash
docker-compose logs -f --tail=100
```

**Native:**
Logs are written to stdout/stderr. Redirect to file:
```bash
python -m src.db_clone_tool.main > app.log 2>&1
```

---

## Backup and Recovery

### Backup

```bash
# Connections and configuration
tar -czf backup-config-$(date +%Y%m%d).tar.gz config.local/

# Exported SQL files
tar -czf backup-exports-$(date +%Y%m%d).tar.gz tmp/exports/

# Complete backup
tar -czf backup-complete-$(date +%Y%m%d).tar.gz config.local/ tmp/
```

### Recovery

```bash
# Extract backup
tar -xzf backup-config-20260126.tar.gz

# Verify
ls -la config.local/

# Restart application
docker-compose restart  # Docker
# or
./run.sh  # Native
```

---

## Scaling

### Multiple Instances (Load Balancing)

**Docker Compose Scale:**
```bash
docker-compose up -d --scale db-clone-tool=3
```

**Nginx Load Balancer:**
```nginx
upstream db_clone_pool {
    server localhost:5001;
    server localhost:5002;
    server localhost:5003;
}

server {
    location / {
        proxy_pass http://db_clone_pool;
    }
}
```

---

## Support

**Documentation:**
- README.md - Quick start guide
- docs/DEPLOYMENT.md - This file
- docs/RELEASING.md - Release process guide

**Issues:**
- GitHub: https://github.com/melihcelenk/db-clone-tool/issues

**Health Check Endpoint:**
- GET `/api/health` - Service status

---

**Last Updated:** 2026-02-25
**Version:** 0.2.0
