# Docker Setup Guide for PyAuthService

This guide covers Docker deployment, development, and troubleshooting for PyAuthService.

## Quick Start

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Start all services
docker-compose up -d

# 3. Check if everything is running
docker-compose ps

# 4. View logs
docker-compose logs -f app

# 5. Access application
# App: http://localhost:8000
# Admin: http://localhost:8000/admin (user: admin, pass: admin)
```

## File Structure

```
pyauthservice/
├── Dockerfile              # Official production Dockerfile
├── docker-compose.yml      # Production-ready compose file
├── docker-compose.override.yml  # Development overrides (not git-tracked)
├── .dockerignore           # Files to exclude from Docker build
├── entrypoint.sh           # Container startup script (runs migrations)
├── docker-validate.sh      # Script to validate Docker setup
├── Makefile               # Convenient Docker commands
├── .env.example           # Environment template
└── .env                   # Your secrets (never commit!)
```

## Services

### Forwarding oauth2-proxy access tokens

When oauth2-proxy protects this service, configure it to forward the OAuth access
token rather than forwarding its session cookie to Django. Use the settings in
`oauth2-proxy.env.example`, especially:

```text
OAUTH2_PROXY_PASS_ACCESS_TOKEN=true
OAUTH2_PROXY_SET_AUTHORIZATION_HEADER=true
```

If Nginx uses `auth_request`, copy the access-token response header from the
oauth2-proxy subrequest to the upstream request:

```nginx
location /api/ {
    auth_request /oauth2/auth;
    auth_request_set $access_token $upstream_http_x_auth_request_access_token;
    proxy_set_header Authorization "Bearer $access_token";
    proxy_pass http://pyauthservice:8000;
}

location = /oauth2/auth {
    internal;
    proxy_pass http://oauth2-proxy:4180/oauth2/auth;
    proxy_pass_request_body off;
    proxy_set_header Content-Length "";
    proxy_set_header X-Original-URI $request_uri;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Host $http_host;
}
```

The Django API continues to authenticate the forwarded token using
`SSOJWTAuthentication`; the SPA only makes same-origin requests with its
oauth2-proxy session cookie:

```javascript
fetch('/api/users/', { credentials: 'include' })
```

Do not expose the session cookie or client secret to browser JavaScript.

### Resource-bound API tokens

The authorization server uses OAuth 2.0 resource indicators (RFC 8707) to bind
new API tokens to one or more API resource URIs. API scope names/descriptions
and global default scopes are tracked in `oauth/scope_catalog.py`; per-client
resource permissions are best configured in Django admin. Existing deployments
can still use the environment fallback, for example:

```text
OAUTH2_RESOURCE_POLICIES={"nginx-gateway":{"https://pocketbase.example.com/":["pocketbase:access"]}}
```

Replace the example client ID and URI with the registered OAuth client and the
canonical HTTPS base URI PocketBase will use as its audience. Configure the
client to request that `resource` and scope. The requested resource must be
allowlisted for that client, and resource-specific scopes cannot be issued
without an allowed resource. The project signs the resource URI into JWT `aud`;
Django OAuth Toolkit 3.4.1+ stores the resource on the grant/token and returns
it as `aud` from `/o/introspect/`.

For an existing client that does not send `resource` or `scope`, configure
`OAUTH2_CLIENT_DEFAULTS` to supply those values. For example:

```text
OAUTH2_CLIENT_DEFAULTS={"nginx-gateway":{"resources":["https://pocketbase.example.com/"],"scopes":["openid","email","profile","pocketbase:access"]}}
```

Clients without an entry use `OAUTH2_DEFAULT_AUDIENCE` and the catalog's
`DEFAULT_SCOPE_NAMES`; these preserve the current legacy audience and core
scopes. This allows clients to migrate by configuration without requiring each
client to change its OAuth request immediately. Do not add an API scope to
global defaults: API scopes should only be defaulted for a client that is
allowlisted for the matching resource.

### Managing client policies in Django admin

Client policies can also be managed in the Django admin without editing JSON
environment variables. After deploying, run `python manage.py migrate`, then
open **OAuth2 Provider > Applications** and edit the client. The application
form includes:

- **Client default scopes**: scopes applied only when the client does not send
    a `scope` parameter. Leave empty to use the global default scopes.
- **Allowed API resources and scopes**: add each canonical HTTPS resource URI
    and select the API scopes that client may obtain for it. Mark at most one
    resource as the default audience; that resource is used only when the client
    omits `resource`.

Resource scope choices come from `API_SCOPE_CATALOG` in
`oauth/scope_catalog.py`. Add new API scope names/descriptions there, add a
scope to `DEFAULT_SCOPE_NAMES` only when it should be requested by default, then
deploy the code. OIDC identity scopes such as `openid`, `email`,
and `profile` are not resource permissions and are not offered in the resource
policy selector. A configured admin policy takes
precedence over environment policy for that OAuth client. Clients without an
admin policy continue to use `OAUTH2_CLIENT_DEFAULTS` and
`OAUTH2_RESOURCE_POLICIES`, so the change can be rolled out one client at a
time. Explicit OAuth request scopes/resources remain subject to that client's
allowed resource policy; defaults do not grant permissions by themselves.
Existing authorization grants and refresh tokens keep their original resource
binding. A client newly given a default audience must complete a fresh
authorization flow before it receives tokens bound to that audience; refresh
tokens do not gain newly configured resource access.

Clients without an admin default resource and without an environment default
resource retain the legacy `default-resource-service` audience. Keep those
clients unchanged during migration. After deploying the new Toolkit version,
run `python manage.py migrate`
before enabling resource-bound issuance; the Toolkit migration adds resource
fields to grants, access tokens, and refresh tokens. Migrate clients API by API,
and do not change the existing default audience until its consumers have moved.
OAuth2 Proxy versions/configurations differ in whether they can send the RFC
8707 `resource` parameter, so verify the authorization request and resulting
token before enabling the corresponding resource policy.

OAuth access- and refresh-token lifetimes can be configured with
`OAUTH2_ACCESS_TOKEN_EXPIRE_SECONDS` and
`OAUTH2_REFRESH_TOKEN_EXPIRE_SECONDS`. The refresh lifetime is measured from
the associated access token's expiry. The default is 365 days, so oauth2-proxy
sessions older than that can no longer refresh and users must sign in again.
Increasing the configured lifetime affects refresh tokens still present and
valid in the database; it cannot restore tokens that have already been revoked
or removed by token cleanup.

### React SPA with the same SSO session

Register the SPA as a separate **public** OAuth application. Use the
authorization-code flow with PKCE and do not give the SPA a client secret:

```text
Client type: Public
Grant type: Authorization code
Redirect URI: https://analytics.hacksaw.in/auth/callback
Scopes: openid email profile
Algorithm: RS256
```

The SPA should use an OIDC client library with PKCE. Its browser flow is:

```text
analytics.hacksaw.in -> auth.hacksaw.in/o/authorize/
                     -> existing SSO login session
                     -> /auth/callback?code=...
                     -> POST /o/token/ with code_verifier
                     -> API with Authorization: Bearer <access_token>
```

The SPA API request is then:

```javascript
fetch('https://api.hacksaw.in/api/users/', {
    headers: { Authorization: `Bearer ${accessToken}` },
});
```

For production, set `OAUTH2_PKCE_REQUIRED=True` only after every authorization
code client, including oauth2-proxy, is configured to send S256 PKCE.

### App Service
**Image**: `pyauthservice:latest` (built locally)  
**Port**: 8000  
**Database**: PostgreSQL provided by the Compose `db` service

The entrypoint script automatically:
- Waits for database to be ready
- Runs `python manage.py migrate`
- Collects static files
- Creates default superuser (dev only)

The Compose configuration provisions PostgreSQL as the `db` service. Its data is persisted in the `postgres_data` Docker volume. Set `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` in `.env`; the application connects to `db:5432` over the private Compose network.

## Development Workflow

### Run Development Server with Hot Reload

The `docker-compose.override.yml` automatically loads and applies:
- Django development server instead of gunicorn
- `/app` volume mount for instant code reloading
- Debug mode enabled

```bash
# Start with auto-reload
docker-compose up -d

# Edit your code, changes appear instantly!
# View logs:
docker-compose logs -f app
```

### Common Development Tasks

```bash
# Run migrations
docker-compose exec app python manage.py migrate

# Create database
docker-compose exec app python manage.py migrate --run-syncdb

# Create superuser
docker-compose exec app python manage.py createsuperuser

# Run tests
docker-compose exec app python manage.py test

# Django shell
docker-compose exec app python manage.py shell

# Jump into container
docker-compose exec app bash

# View logs
docker-compose logs -f app

# Stop all services
docker-compose down

# Full restart
docker-compose down && docker-compose up -d
```

### Using Makefile Shortcuts

```bash
make docker-build      # Rebuild images
make docker-up         # Start services
make docker-down       # Stop services
make docker-logs       # View live logs
make docker-shell      # Jump into container
make docker-migrate    # Run migrations
make docker-superuser  # Create superuser
make docker-restart    # Full restart
make docker-clean      # Remove all containers & volumes
make docker-help       # Show all commands
```

## Environment Configuration

### `.env` File

Create `.env` from `.env.example`:

```bash
cp .env.example .env
```

**Key variables:**
- `DEBUG`: Set to `False` for production
- `SECRET_KEY`: Must be secret in production
- `POSTGRES_*`: PostgreSQL connection settings
- `ALLOWED_HOSTS`: Comma-separated list of allowed domains
- `SERVICE_API_TOKEN`: API token for special endpoints

### Production vs Development

**Development** (docker-compose.override.yml):
- `DEBUG=True`
- Django dev server
- Hot reload enabled
- Automatic superuser creation

**Production** (docker-compose.yml):
- `DEBUG=False`
- Gunicorn app server
- 4 workers, 120s timeout
- Manual secrets management

## Building & Publishing

### Build Image Locally

```bash
# Build from Dockerfile
docker-compose build

# Or with BuildKit (faster)
DOCKER_BUILDKIT=1 docker build -t pyauthservice:latest .
```

### View Image Size

```bash
docker images | grep pyauthservice
```

### Publish to Registry

```bash
# Tag image
docker tag pyauthservice:latest myregistry/pyauthservice:v1.0.0

# Push to registry (Docker Hub, ECR, etc)
docker push myregistry/pyauthservice:v1.0.0
```

## Database Management

### Backup Database

```bash
# Backup PostgreSQL
docker-compose exec db pg_dump -U authuser pyauthservice > backup.sql

# Or via docker
docker exec pyauthservice-db pg_dump -U authuser pyauthservice > backup.sql
```

### Restore Database

```bash
# Restore from backup
docker-compose exec -T db psql -U authuser pyauthservice < backup.sql
```

### Access Database CLI

```bash
docker-compose exec db psql -U authuser -d pyauthservice

# Inside psql:
# \dt                           # List tables
# SELECT * FROM users_user;     # Query users
# \q                            # Exit
```

## Troubleshooting

### "Port already in use"
```bash
# Change port in docker-compose.yml
# Change: "8000:8000"  to  "8001:8000"

docker-compose up -d
```

### "Database connection refused"
```bash
# Wait for database to start
sleep 10
docker-compose up -d

# Or check database logs
docker-compose logs db
```

### "Module not found"
```bash
# Rebuild to install new dependencies
docker-compose build
docker-compose up -d
```

### "Static files not found"
```bash
# Collect static files
docker-compose exec app python manage.py collectstatic --noinput
```

### Slow build
```bash
# Ensure .dockerignore is optimized
# Rebuild without cache
docker-compose build --no-cache
```

### Container exits immediately
```bash
# Check logs for errors
docker-compose logs app

# Try manual migration
docker-compose run --rm app python manage.py migrate
```

### Disk space issues
```bash
# Clean up unused Docker resources
docker system prune -a

# Remove stopped containers
docker container prune

# Remove unused volumes
docker volume prune
```

## Security Best Practices

### 1. Never Commit Secrets
✅ `.env` is in `.gitignore`  
❌ Don't add real secrets to `docker-compose.yml`

### 2. Use Strong Secrets
```bash
# Generate random secret
python -c "import secrets; print(secrets.token_urlsafe(50))"

# Add to .env
SECRET_KEY=<generated-value>
```

### 3. Limit Container Permissions
The app runs as non-root user `appuser` for security.

### 4. Keep Images Updated
```bash
# Pull latest base images
docker-compose build --pull
docker-compose up -d
```

### 5. Scan for Vulnerabilities
```bash
# If available
docker scan pyauthservice:latest
trivy image pyauthservice:latest
```

## Production Deployment

### AWS EC2 Deployment
See the [Docker Implementation Guide](https://github.com/ankithsajikumar/pyauthservice) for complete AWS EC2 setup:
- EC2 instance configuration
- Nginx reverse proxy
- SSL/HTTPS with Let's Encrypt
- GitHub Actions CI/CD
- Monitoring and backups

### Docker Swarm / Kubernetes
Modify `docker-compose.yml`:
- Add resource limits
- Add restart policies
- Configure health checks
- Use secrets management

### Health Checks
The Dockerfile includes health checks:
```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python -c "import http.client; ..."
```

## Logs & Monitoring

### View Service Logs
```bash
docker-compose logs              # All services
docker-compose logs app          # App only
docker-compose logs -f app       # Follow app logs
docker-compose logs --tail=50    # Last 50 lines
```

### Monitor Resources
```bash
# CPU, Memory, Network usage
docker stats

# Container details
docker inspect pyauthservice-app
```

## Useful References

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/compose-file/)
- [Django Deployment](https://docs.djangoproject.com/en/3.2/howto/deployment/wsgi/gunicorn/)
- [PostgreSQL Docker](https://hub.docker.com/_/postgres)
