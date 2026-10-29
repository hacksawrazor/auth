# PyAuthService - Django OAuth2/JWT Authentication Service
# Multi-stage, multi-target build separating dev/test and production environments.

# ==============================================================================
# Stage 1: builder (Base wheel builder for production dependencies)
# ==============================================================================
FROM python:3.11-alpine AS builder

WORKDIR /app

# Install build-time dependencies for native C extensions (psycopg2, cryptography, etc.)
RUN apk add --no-cache \
    gcc \
    musl-dev \
    postgresql-dev \
    libffi-dev \
    binutils

# Create an isolated production virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Strip binary debug symbols and prune caches from installed packages
RUN find /opt/venv -name "*.so" -exec strip --strip-unneeded {} + 2>/dev/null || true && \
    find /opt/venv -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type f -name "*.pyc" -delete && \
    find /opt/venv -type f -name "*.pyo" -delete

# ==============================================================================
# Stage 2: dev-builder (Extends builder with dev/test packages like pytest, flake8)
# ==============================================================================
FROM builder AS dev-builder

COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

# ==============================================================================
# Stage 3: runtime-base (Common minimal Alpine runtime)
# ==============================================================================
FROM python:3.11-alpine AS runtime-base

WORKDIR /app

# Install essential runtime packages: PostgreSQL C client and bash
RUN apk add --no-cache \
    libpq \
    bash && \
    rm -rf /usr/local/lib/python3.11/idlelib && \
    rm -rf /usr/local/lib/python3.11/ensurepip

# Create unprivileged user (UID 1000) and prepare static/log dirs
RUN adduser -D -u 1000 appuser && \
    mkdir -p /app/staticfiles /app/logs && \
    chown -R appuser:appuser /app

# Runtime environment settings
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python -c "import http.client; conn = http.client.HTTPConnection('localhost', int('${PORT}')); conn.request('GET', '/health/'); exit(0 if conn.getresponse().status == 200 else 1)" || exit 1

# ==============================================================================
# Stage 4: dev (Target: Development and CI test runner)
# ==============================================================================
FROM runtime-base AS dev

# Extra tools needed for testing and certificate generation in CI
RUN apk add --no-cache openssl

# Copy dev virtualenv (includes pytest, flake8, and test dependencies)
COPY --from=dev-builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy full codebase INCLUDING tests
COPY --chown=appuser:appuser . .
RUN chmod +x /app/entrypoint.sh

USER appuser

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ==============================================================================
# Stage 5: prod (Target: Production image without tests or dev tools)
# ==============================================================================
FROM runtime-base AS prod

# Copy lean production virtualenv (NO pytest, NO flake8, NO test tools)
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application files
COPY --chown=appuser:appuser . .

# Prune test files, test configs, and dev files from production image
RUN rm -rf /app/users/test*.py \
           /app/oauth/test*.py \
           /app/virtual_permissions/test*.py \
           /app/pytest.ini \
           /app/requirements-dev.txt \
           /app/.coveragerc && \
    chmod +x /app/entrypoint.sh

USER appuser

# Production WSGI server
CMD ["gunicorn", "pyauthservice.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]
