import jwt
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from cryptography.hazmat.primitives import serialization
import logging
from oauth2_provider.oauth2_validators import validate_resource_as_url_prefix

logger = logging.getLogger(__name__)


class SSOJWTAuthentication(BaseAuthentication):
    """
    Authenticate requests using JWTs issued by this SSO.
    """

    @staticmethod
    def _audience_matches(request, payload):
        audiences = payload.get("aud")
        if isinstance(audiences, str):
            audiences = [audiences]
        if not isinstance(audiences, list) or not all(isinstance(audience, str) for audience in audiences):
            logger.debug("Rejecting JWT with missing or malformed audience claim")
            return False
        if audiences == [settings.OAUTH2_DEFAULT_AUDIENCE]:
            logger.debug("JWT matched configured legacy audience")
            return True

        request_uri = request.build_absolute_uri().split("?", 1)[0]
        matched = validate_resource_as_url_prefix(request_uri, audiences)
        logger.debug(
            "JWT resource audience check %s for request URI %s against %d audience(s)",
            "passed" if matched else "failed",
            request_uri,
            len(audiences),
        )
        return matched

    def authenticate(self, request):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.debug("No Bearer authorization header; allowing other authenticators to run")
            return None  # let other authenticators run (or AnonymousUser)

        token = auth_header.split(" ")[1]

        try:
            # Load public key from private key
            private_key = settings.OAUTH2_PROVIDER["OIDC_RSA_PRIVATE_KEY"]
            public_key = serialization.load_pem_private_key(
                private_key.encode(),
                password=None,
            ).public_key()
            public_key_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ).decode()

            # Decode the token
            payload = jwt.decode(
                token,
                public_key_pem,
                algorithms=["RS256"],
                options={"verify_aud": False},
                issuer=settings.OAUTH2_PROVIDER["OIDC_ISS_ENDPOINT"],
            )
        except jwt.ExpiredSignatureError:
            logger.info("Rejected expired JWT access token")
            raise exceptions.AuthenticationFailed("Token expired")
        except jwt.InvalidTokenError as e:
            logger.info("Rejected invalid JWT access token (%s)", type(e).__name__)
            raise exceptions.AuthenticationFailed("Invalid token")

        if not self._audience_matches(request, payload):
            logger.info("Rejected JWT access token because its audience did not match this API")
            raise exceptions.AuthenticationFailed("Invalid token audience")

        # Get user from the token payload
        User = get_user_model()
        user = None
        if "sub" in payload:
            try:
                user = User.objects.get(username=payload["sub"])
            except User.DoesNotExist:
                user = AnonymousUser()

        logger.debug(
            "Authenticated JWT access token for this API: scope_count=%d",
            len(str(payload.get("scope", "")).split()),
        )
        return (user, payload)
