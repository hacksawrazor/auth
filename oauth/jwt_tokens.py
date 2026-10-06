import time, uuid, jwt
from django.conf import settings
from oauthlib.common import generate_token
from oauth2_provider.utils import jwk_from_pem

def get_token_user(request):
    if getattr(request, "user", ""):
        return request.user.get_username()
    elif getattr(request, "client", "") and getattr(request.client, "user", ""):
        return request.client.user.get_username()
    return ""


def jwt_access_token_generator(request):
    now = int(time.time())
    exp = now + settings.OAUTH2_PROVIDER.get("ACCESS_TOKEN_EXPIRE_SECONDS", 3600)

    # RFC 8707 resource indicators become JWT audiences. Unbound legacy clients
    # use the deployment-configured fallback audience.
    audiences = getattr(request, "resource", None) or [settings.OAUTH2_DEFAULT_AUDIENCE]
    if isinstance(audiences, str):
        audiences = [audiences]

    payload = {
        "iss": settings.OAUTH2_PROVIDER["OIDC_ISS_ENDPOINT"],
        "sub": get_token_user(request),
        "aud": audiences,
        "iat": now,
        "exp": exp,
        "jti": str(uuid.uuid4()),
        "client_id": getattr(request, "client_id", None),
        "scope": " ".join(request.scopes or []),
        "grant_type": getattr(request, "grant_type", ""),
    }

    private_key = settings.OAUTH2_PROVIDER["OIDC_RSA_PRIVATE_KEY"]
    key = jwk_from_pem(private_key)
    kid = key.thumbprint()
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": kid})


def opaque_refresh_token_generator(request):
    return generate_token(32)
