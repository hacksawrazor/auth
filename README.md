# PyAuthService

A Django-based authentication service providing SSO (Single Sign-On) and user management APIs, supporting OAuth2.

---

## Features

- Custom user model
- User management API (CRUD)
- OAuth2 authentication
- Django admin interface for user and OAuth application management
- Health check endpoint

---

## 🐳 Quick Start with Docker (Recommended)

The fastest way to get started is using Docker and Docker Compose. The app runs migrations against the PostgreSQL database configured in `.env`.

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)

### Setup
```sh
# 1. Clone and enter directory
git clone https://github.com/ankithsajikumar/pyauthservice.git
cd pyauthservice

# 2. Copy environment template and customize
cp .env.example .env

# 3. Start the app
docker-compose up -d

# Container runs migrations and creates superuser automatically!
```

### Access Services
- **App**: http://localhost:8000
- **Admin**: http://localhost:8000/admin (username: `admin`, password: `admin`)
- **API**: http://localhost:8000/api/
- **Database**: PostgreSQL configured with `POSTGRES_*` variables in `.env`

### Useful Docker Commands
```sh
make docker-help              # Show all available commands
make docker-logs              # View live application logs
make docker-shell             # Jump into app container
make docker-migrate           # Run migrations manually
make docker-superuser         # Create another superuser
make docker-down              # Stop all services
docker-compose ps             # List running containers
docker-compose exec app bash  # Run shell commands in app
```

### Deployment to AWS EC2
For production deployment with HTTPS, SSL certificate auto-renewal, CI/CD automation, and backups, see the [Docker Implementation Guide](https://github.com/ankithsajikumar/pyauthservice/wiki/Docker-EC2-Deployment).

---

## 🚀 Traditional Setup (Without Docker)

### Getting Started

### 1. Clone the repository

```sh
git clone https://github.com/ankithsajikumar/pyauthservice.git
cd pyauthservice
```

### 2. Set up a virtual environment

```sh
python3 -m venv venv
source venv/bin/activate
```

### 3. Install requirements

```sh
pip install -r requirements.txt
```

### 4. Apply migrations

```sh
python manage.py migrate
```

### 5. Create a superuser

```sh
python manage.py createsuperuser
```

### 6. Run the development server

```sh
python manage.py runserver
```

### MISC: Deactivate venv

```sh
deactivate
```

### MISC: Store dependencies

```sh
pip freeze > requirements.txt
```

---

## API Endpoints

- **Root Redirect:**  
  - `GET /` — Redirects to the Django admin interface at `/admin/`
    ```sh
    curl -v https://domain/
    ```
    > You will receive an HTTP 302 redirect to `/admin/`.

- **User Management:**  
  - `GET /api/users/` — List users  
    ```sh
    curl -H "Authorization: Bearer <oidc_access_token>" https://domain/api/users/
    ```
  - `POST /api/users/` — Create user  
    ```sh
    curl -X POST https://domain/api/users/ \
      -H "Content-Type: application/json" \
      -d '{
        "username": "newuser",
        "password": "newpassword",
        "email": "newuser@example.com",
        "first_name": "First Name",
        "last_name": "Last Name"
      }'
    ```
    > Only staff users can set `is_staff` or `is_active` fields. Required fields are `username`, `password`, `email`.

  - `GET /api/users/<id>/` — Retrieve user  
    ```sh
    curl -H "Authorization: Bearer <oidc_access_token>" https://domain/api/users/1/
    ```
  - `PUT/PATCH /api/users/<id>/` — Update user  
    ```sh
    curl -X PATCH https://domain/api/users/1/ \
      -H "Authorization: Bearer <oidc_access_token>" \
      -H "Content-Type: application/json" \
      -d '{"first_name": "UpdatedName"}'
    ```
  - `DELETE /api/users/<id>/` — Delete user  
    ```sh
    curl -X DELETE https://domain/api/users/1/ \
      -H "Authorization: Bearer <access_token>"
    ```

  - `GET /auth/me/` — Get current authenticated user's info  
    ```sh
    curl -H "Authorization: Bearer <oidc_access_token>" https://domain/auth/me/
    ```
    > Returns the authenticated user's details.

- **OAuth2:**  
  - `/o/` — OAuth2 endpoints (see [django-oauth-toolkit docs](https://django-oauth-toolkit.readthedocs.io/en/latest/))
  - `POST /api/login/` — Login endpoint 
    ```sh
    curl -X POST https://domain/api/login/ \
      -H "Content-Type: application/json" \
      -d '{"username": "user", "password": "password"}'
    ```
  - `POST /api/logout/` — Logout endpoint  
    ```sh
    curl -X POST https://domain/api/logout/ \
    ```

- **Health:**
  - `GET /health/` — Basic service health check
    ```sh
    curl https://domain/health/
    ```
    > Returns `{ "status": "ok" }`.

---

## Authentication

- **OAuth2:**  
  Standard OAuth2 flows are available at `/o/`.

---

## Useful Django Commands

- Run development server:  
  `python manage.py runserver`
- Make migrations:  
  `python manage.py makemigrations`
- Apply migrations:  
  `python manage.py migrate`
- Create superuser:  
  `python manage.py createsuperuser`
- Open Django shell:  
  `python manage.py shell`
- Collect static files:  
  `python manage.py collectstatic`

---

## Project Structure

```
pyauthservice/
├── manage.py
├── requirements.txt
├── README.md
├── users/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── ...
└── pyauthservice/
    ├── settings.py
    ├── urls.py
    └── ...
```

---

## Environment Variables (`.env`)

This project uses a `.env` file to manage sensitive settings and environment-specific configuration.  
Create a `.env` file in your project root (same directory as `manage.py`) with the following variables:

| Variable             | Description                                      |
|----------------------|--------------------------------------------------|
| `SECRET_KEY`         | Django secret key for cryptographic signing      |
| `DEBUG`              | Set to `True` for development, `False` for prod  |
| `ALLOWED_HOSTS`       | Additional comma-separated hostnames for production |
| `CSRF_TRUSTED_ORIGINS` | Additional comma-separated HTTPS origins for CSRF |
| `CORS_ALLOWED_ORIGINS` | Additional comma-separated frontend origins for CORS |
| `OIDC_ISS_ENDPOINT`  | Auth service domain url passed with OIDC token          |
| `OIDC_RSA_PRIVATE_KEY` | Inline OIDC RSA private key in PEM format      |
| `OIDC_PRIVATE_KEY_PATH` | Path to an OIDC RSA private key PEM file      |

**Example `.env` file:**
```env
SECRET_KEY=<django-secret-key>
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
OIDC_ISS_ENDPOINT=<auth-service-domain>
OIDC_PRIVATE_KEY_PATH=/path/to/oidc_private.pem
```

`localhost` and `127.0.0.1` are included by default for development. Add the
production values as comma-separated entries in `.env`:

```env
ALLOWED_HOSTS=apis.hacksaw.in,auth.hacksaw.in
CSRF_TRUSTED_ORIGINS=https://apis.hacksaw.in,https://auth.hacksaw.in
CORS_ALLOWED_ORIGINS=https://hacksaw.in
```

Environment values are merged with the defaults and duplicate entries are
removed.

> **Note:** Never commit your `.env` file with real secrets to version control. Use `.env.example` as a template.

---

> **Note:** Configure the OIDC RSA private key with `OIDC_RSA_PRIVATE_KEY`, `OIDC_PRIVATE_KEY_PATH`, or an `oidc_private.pem` file in the project root.

---

### GitHub Actions Deploy Prerequisites

Before running the deploy workflow, set the following in your repository:

#### Repository Variables (`Settings > Variables > Actions`)
- `CONSOLE_USER_ID`: PythonAnywhere username

#### Repository Secrets (`Settings > Secrets > Actions`)
- `CONSOLE_API_KEY`: PythonAnywhere API token (get from your PythonAnywhere account)

These are required for the workflow to authenticate with PythonAnywhere.

## License

MIT License