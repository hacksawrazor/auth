"""Source-controlled OAuth scope descriptions and default scope names."""

STANDARD_SCOPES = {
    "read": "Read-only access",
    "write": "Write access",
}

IDENTITY_SCOPES = {
    "openid": "OpenID Connect scope",
    "offline_access": "Maintain access when the user is not present",
    "email": "Access to the user's email address",
    "profile": "Access to the user's profile information",
}

API_SCOPE_CATALOG = {
    "pocketbase:access": "Access to the PocketBase API",
}

SCOPE_CATALOG = {
    **STANDARD_SCOPES,
    **IDENTITY_SCOPES,
    **API_SCOPE_CATALOG,
}

DEFAULT_SCOPE_NAMES = (
    "read",
    "write",
    "openid",
    "offline_access",
    "email",
    "profile",
)