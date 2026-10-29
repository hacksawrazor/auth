# PyAuthService - Django OAuth2/JWT Authentication Service
# Multi-stage Alpine build optimized for minimal image size and security.

# Stage 1: Build wheels and virtual environment
FROM python:3.11-alpine AS builder

WORKDIR /app

# Install build-time dependencies for native C extensions (psycopg2, cryptography, etc.)
RUN apk add --no-cache \
    gcc \
    musl-dev \
    postgresql-dev \
    libffi-dev \
    binutils

# Create an isolated virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Strip binary debug symbols and prune test suites / caches from installed packages
RUN find /opt/venv -name "*.so" -exec strip --strip-unneeded {} + 2>/dev/null || true && \
    find /opt/venv -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type d -name "tests" -prune -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type d -name "test" -prune -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type f -name "*.pyc" -delete && \
    find /opt/venv -type f -name "*.pyo" -delete

# Stage 2: Minimal runtime image
FROM python:3.11-alpine

WORKDIR /app

# Install only essential runtime packages:
# - libpq: PostgreSQL C client library
# - bash: compatibility with entrypoint.sh, CI runner, and developer shell
RUN apk add --no-cache \
    libpq \
    bash

# Clean unnecessary standard library files from base Python
RUN find /usr/local/lib/python3.11 -type d -name "test" -prune -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.11 -type d -name "tests" -prune -exec rm -rf {} + 2>/dev/null || true && \
    rm -rf /usr/local/lib/python3.11/idlelib && \
    rm -rf /usr/local/lib/python3.11/ensurepip

# Copy optimized virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create unprivileged user (UID 1000) and prepare static/log dirs
RUN adduser -D -u 1000 appuser && \
    mkdir -p /app/staticfiles /app/logs && \
    chown -R appuser:appuser /app

# Copy application files with non-root ownership
COPY --chown=appuser:appuser . .

RUN chmod +x /app/entrypoint.sh

# Runtime environment settings
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

USER appuser

EXPOSE ${PORT}

# Native Python health check (no curl/wget dependency needed)
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python -c "import http.client; conn = http.client.HTTPConnection('localhost', int('${PORT}')); conn.request('GET', '/health/'); exit(0 if conn.getresponse().status == 200 else 1)" || exit 1

# Production WSGI server
CMD ["gunicorn", "pyauthservice.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]
