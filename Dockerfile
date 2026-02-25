# Multi-stage build for MySQL Schema Clone Tool
# Stage 1: Extract MySQL binaries from official MySQL image
FROM mysql:8.0.40 AS mysql-binaries

# Stage 2: Build application image
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 3: Final production image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DB_CLONE_MYSQL_BIN=/app/mysql/bin \
    DB_CLONE_MYSQL_VERSION=8.0.40 \
    DB_CLONE_CONFIG_DIR=/app/config.local

# Install runtime dependencies for MySQL binaries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libncurses6 \
    && rm -rf /var/lib/apt/lists/*

# Create app user (non-root for security)
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/mysql/bin /app/config.local && \
    chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Copy MySQL binaries from stage 1
COPY --from=mysql-binaries --chown=appuser:appuser \
    /usr/bin/mysql \
    /usr/bin/mysqldump \
    /app/mysql/bin/

# Copy Python packages from builder
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser . .

# Install application in editable mode
USER appuser
ENV PATH=/home/appuser/.local/bin:$PATH
RUN pip install --user -e .

# Expose Flask port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/health').read()" || exit 1

# Run application
CMD ["python", "-m", "src.db_clone_tool.main"]
