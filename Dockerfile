# Multi-stage build for 3D Print CAD Assistant
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements files
COPY requirements.txt requirements_web.txt /tmp/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    pip install --no-cache-dir -r /tmp/requirements_web.txt

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash caduser && \
    mkdir -p /app /data/uploads /data/results /data/cache /data/logs && \
    chown -R caduser:caduser /app /data

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=caduser:caduser . /app/

# Switch to non-root user
USER caduser

# Environment variables
ENV FLASK_APP=src.web.app:create_app \
    PYTHONPATH=/app \
    UPLOAD_FOLDER=/data/uploads \
    RESULTS_FOLDER=/data/results \
    CACHE_DIR=/data/cache \
    LOG_DIR=/data/logs

# Expose ports
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/api/health')"

# Default command
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "4", \
     "--threads", "2", \
     "--timeout", "120", \
     "--log-level", "info", \
     "--access-logfile", "/data/logs/access.log", \
     "--error-logfile", "/data/logs/error.log", \
     "src.web.app:create_app()"]