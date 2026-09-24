# Adding Unit Testing Efficiently — Auth Service

Based on repo state: Django 5.2, existing `users/tests.py`, `manage.py`, `settings.py` (postgres/sqlite split), `docker-compose.yml`, no `pytest.ini` or `setup.cfg`.

## 1. Start with Django built-in (fastest, zero new packages)

```bash
# Run existing
python manage.py test users.tests

# All apps
python manage.py test

# With DB override for speed (sqlite in-memory for CI)
DB_ENGINE=sqlite3 DEBUG=True python manage.py test users
```

- `users/tests.py` is the existing home; add more per module (`users/test_auth.py`, `pyauthservice/test_settings.py`).
- Use `django.test.TestCase` (transactions per test) for DB work; `TransactionTestCase` only if testing transaction behavior explicitly.
- For session/auth tests, use Django `Client` (`self.client.post('/login/', ...)`) — matches real `/login/` and `/logout/` routes.

## 2. Where to put tests (choose one, consistent)

- Per-app: `users/tests/` (split by feature: `test_login_view.py`, `test_oidc_flow.py`).
- Root: `tests/` (for cross-app / integration). Keep `users/tests.py` for user-model tests.
- For OIDC/auth integration: test against `/o/authorize/` using `django.test.Client`; mock `oauth2_provider` tokens only if testing provider behavior (keep real provider for integration tests).

## 3. Test config (no new files needed)

In `pyauthservice/settings.py` (already env-driven):

```python
# For CI / fast runs, override via env or a test settings module:
DATABASES['default'] = {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': ':memory:',
}
```

Or create `pyauthservice/test_settings.py` that imports from settings and overrides DB + `DEBUG=True`; point with:

```bash
DJANGO_SETTINGS_MODULE=pyauthservice.test_settings python manage.py test
```

If using PostgreSQL in CI, create a separate test DB (`auth_test`) and set `TEST = {'NAME': 'auth_test'}` in environment.

## 4. If you want pytest (optional)

Add to `requirements.txt` (only if chosen):
- `pytest>=7`
- `pytest-django>=4`
- `pytest-mock` (optional)

Create minimal `pytest.ini` at repo root:

```
[pytest]
DJANGO_SETTINGS_MODULE = pyauthservice.settings
python_files = tests.py test_*.py *_tests.py
```

Then:

```bash
pytest users/ -v --tb=short
```

Keep `manage.py test` as the default; pytest is optional for parameterized fixtures.

## 5. Coverage (optional)

Add `coverage>=7` to requirements; run:

```bash
coverage run --source='pyauthservice,users,oauth' manage.py test
coverage report -m
```

## 6. What to test first (ordered by value / risk)

1. `users/login.html` / `users/login_success.html` renders (template load, context `next`).
2. `user_login_view` — redirect to `next`, session creation, error message, authenticated-visit success page (the loop fix), CSRF.
3. `user_logout_view` — logout clears session, redirects to `/login/`.
4. `/login/` + `/logout/` URL resolution (no 404, names match).
5. `/o/authorize/` basic resolution (confirm OAuth2 provider loads; mock token for quick check).
6. `users/signals.py` (OAuth2 `app_authorized`) — mock `token.application`; confirm hook runs.
7. `settings` — `LOGIN_URL`, `LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL`, `ALLOWED_HOSTS`, `REST_FRAMEWORK` auth classes intact.
8. `/api/login/` removed (confirmation that old JSON endpoint no longer resolves).
9. Old `templates/login.html` removed (confirm 404 on old root branded page if referenced).

Avoid testing Django admin internals unless you depend on `/admin/`; it is independent of OIDC.

## 7. Do not test (already covered / out of scope)

- `oauth/jwt_tokens.py` token generation (test inside `oauth2_provider` rather than duplicating).
- `users/signals.py` integration with full OAuth flow unless testing a specific client app.
- `rest_framework_simplejwt` (removed; no tests needed).

## 8. CI / deploy pipeline

If `.github/workflows/deploy.yml` or `docker.yml` rebuilds, add a test stage before deploy:

```yaml
- name: Test
  run: |
    pip install -r requirements.txt
    DB_ENGINE=sqlite3 DEBUG=True python manage.py test
```

This avoids deploying with broken `/login/` or missing `/o/` routes.

---
Quick start (today, without new dependencies):
```bash
DB_ENGINE=sqlite3 DEBUG=True python manage.py test users.tests
```
