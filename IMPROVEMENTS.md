# Optimization / Improvement Audit — Auth Service

Based on current repo state (post-#10 split, post-fixes, current branch).

## Security (must-do before production)
- `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE` missing from settings — add for session/auth cookies.
- `DEBUG` defaults `True` via env; enforce `DEBUG=False` for deploy.
- `SECRET_KEY` env only; no rotation mechanism noted.
- `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` default only localhost/3000 — extend for production hosts (already needed for OIDC as shown in CI fixes).
- `oidc_private.pem` is local secret; should not be in image (already excluded `.gitignore`/`.dockerignore`); for deploy, inject via secret/variable (not file-in-image) or mount at runtime.
- `/login/` has no rate limit / brute-force guard (`django-axes` or middleware) — risk for session auth.
- `users/signals.py` logs token events but has no audit trail / security event logging.

## Performance / Reliability
- `django-cors-headers` and `CORS_ALLOWED_ORIGINS` loaded; if all clients same-origin/proxy, can drop CORS middleware (optional; keep if analytics/sso cross-origin).
- `rest_framework` still loaded (after #10 routes removed; settings still list auth classes); if DRF APIs fully removed, can drop `rest_framework` from INSTALLED_APPS and requirements.
- `virtual_permissions` installed (no MIDDLEWARE reference); check if used — if not, drop.
- `staticfiles` admin assets copied; no WhiteNoise or nginx static serving configured (only `STATIC_ROOT` set).
- `/health/` only checks process — could check DB + OIDC config load.
- `users/login.html` / `users/login_success.html` are responsive but minimal; no asset pipeline (CSS inline). Fine for current use.
- `docker-compose.yml` has `db`; Redis not configured despite `DOCKER.md` mentioning session/cache use. If session/caching needed, add Redis service.
- Build uses legacy `docker build` (deprecated builder); update `.github/workflows/docker.yml` to use `docker buildx` / BuildKit (already uses `docker/setup-buildx-action@v2` for build step but build command uses legacy syntax).

## Tests / Quality (already started with #12–#16)
- `users/test_session_flow.py` uses hardcoded `admin/admin`; should create user in setUp (already fixed in #13?). Verify it uses create_user.
- `users/test_oidc_verify.py` only checks import/resolution — could extend with `Mock` token validation for `SSOJWTAuthentication`.
- No `coverage` config yet (#15 added `pytest.ini` but no `pyproject.toml` or `.coveragerc`).
- `TESTING.md` exists; not linked from README.
- `.vscode/settings.json` exists but not documented.

## Documentation / Deployment
- `README.md` cleaned for JWT but still references `Bearer` in `/api/users/` curl examples (now accurate for OAuth2 tokens, but could clarify OIDC token usage).
- `DOCKER.md` and `DOCKER_IMPLEMENTATION_SUMMARY.md` mention JWT / OAuth2 proxy; could update for pure OIDC session-flow.
- `entrypoint.sh`, `Makefile` — review for stale commands.
- `docker-validate.sh` — verify if it tests the right endpoints.

## Suggested order (confirmed by user for each)
1. Security settings (cookie flags, DEBUG, ALLOWED_HOSTS defaults) — low risk.
2. Drop `virtual_permissions` / `rest_framework` if not needed — medium.
3. Add rate-limit / brute-force guard — medium.
4. Health endpoint expansion — low.
5. Coverage / CI improvements — already started (#16 done).
6. Update docs for pure OIDC.

No destructive edits made. Confirm which to proceed with.
