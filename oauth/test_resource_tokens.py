from datetime import timedelta
import json
from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from oauth2_provider.models import get_access_token_model
from oauth2_provider.oauth2_validators import Grant
from oauth2_provider.views.introspect import IntrospectTokenView

from oauth.authentication import SSOJWTAuthentication
from oauth.validators import UserClaimsValidator
from oauth.jwt_tokens import jwt_access_token_generator
RESOURCE = "https://pocketbase.example.com/"
API_SCOPE = "pocketbase:access"
CLIENT_ID = "nginx-gateway"

RESOURCE_SETTINGS = {
    "OAUTH2_API_SCOPES": {API_SCOPE: "Access to the PocketBase API"},
    "OAUTH2_RESOURCE_POLICIES": {CLIENT_ID: {RESOURCE: [API_SCOPE]}},
    "OAUTH2_CLIENT_DEFAULTS": {CLIENT_ID: {"resources": [RESOURCE], "scopes": [API_SCOPE]}},
    "OAUTH2_DEFAULT_AUDIENCE": "legacy-resource",
    "OAUTH2_DEFAULT_SCOPES": ["openid", "email", "profile"],
    "OAUTH2_PROVIDER": {
        **settings.OAUTH2_PROVIDER,
        "SCOPES": {**settings.OAUTH2_PROVIDER["SCOPES"], API_SCOPE: "Access to the PocketBase API"},
    },
}


class ResourceAudienceTests(SimpleTestCase):
    @patch("oauth.jwt_tokens.jwk_from_pem")
    @patch("oauth.jwt_tokens.jwt.encode", return_value="signed-token")
    def test_resource_becomes_access_token_audience(self, encode, jwk_from_pem):
        jwk_from_pem.return_value.thumbprint.return_value = "key-id"
        request = SimpleNamespace(
            resource=[RESOURCE],
            scopes=[API_SCOPE],
            user=SimpleNamespace(get_username=lambda: "user-1"),
            client_id=CLIENT_ID,
            grant_type="authorization_code",
        )

        jwt_access_token_generator(request)

        payload = encode.call_args.args[0]
        self.assertEqual(payload["aud"], [RESOURCE])

    @patch("oauth.jwt_tokens.jwk_from_pem")
    @patch("oauth.jwt_tokens.jwt.encode", return_value="signed-token")
    def test_unbound_legacy_token_keeps_default_audience(self, encode, jwk_from_pem):
        jwk_from_pem.return_value.thumbprint.return_value = "key-id"
        request = SimpleNamespace(
            scopes=["openid", "email"],
            user=SimpleNamespace(get_username=lambda: "user-1"),
            client_id=CLIENT_ID,
            grant_type="authorization_code",
        )

        jwt_access_token_generator(request)

        self.assertEqual(encode.call_args.args[0]["aud"], [settings.OAUTH2_DEFAULT_AUDIENCE])

    @override_settings(**RESOURCE_SETTINGS)
    def test_resource_scope_requires_allowed_resource_and_client(self):
        validator = UserClaimsValidator()
        client = SimpleNamespace(client_id=CLIENT_ID)

        allowed = SimpleNamespace(client=client, resource=[RESOURCE])
        denied = SimpleNamespace(client=client, resource=["https://other.example.com/"])
        unconfigured_client = SimpleNamespace(client_id="unconfigured-client")
        unbound = SimpleNamespace(client=unconfigured_client, resource=[])

        self.assertTrue(validator.validate_scopes(CLIENT_ID, [API_SCOPE], client, allowed))
        self.assertFalse(validator.validate_scopes(CLIENT_ID, [API_SCOPE], client, denied))
        self.assertFalse(
            validator.validate_scopes("unconfigured-client", [API_SCOPE], unconfigured_client, unbound)
        )

    @override_settings(**RESOURCE_SETTINGS)
    def test_legacy_scopes_remain_valid_without_resource(self):
        validator = UserClaimsValidator()
        client = SimpleNamespace(client_id=CLIENT_ID)
        request = SimpleNamespace(client=client, resource=[])

        self.assertTrue(validator.validate_scopes(CLIENT_ID, ["openid", "email"], client, request))

    @override_settings(**RESOURCE_SETTINGS)
    def test_client_defaults_supply_resource_and_scopes(self):
        validator = UserClaimsValidator()
        client = SimpleNamespace(client_id=CLIENT_ID)
        request = SimpleNamespace(client=client, resource=[])

        self.assertEqual(validator.get_default_scopes(CLIENT_ID, request), [API_SCOPE])
        self.assertEqual(request.resource, [RESOURCE])

    @override_settings(OAUTH2_DEFAULT_SCOPES=["openid", "profile"], OAUTH2_CLIENT_DEFAULTS={})
    def test_global_default_scopes_are_configurable(self):
        validator = UserClaimsValidator()
        client = SimpleNamespace(client_id="existing-client")
        request = SimpleNamespace(client=client, resource=[])

        self.assertEqual(validator.get_default_scopes("existing-client", request), ["openid", "profile"])

    def test_authorization_code_inherits_granted_resource_before_signing(self):
        validator = UserClaimsValidator()
        grant = SimpleNamespace(
            is_expired=lambda: False,
            scope=API_SCOPE,
            user=SimpleNamespace(),
            nonce="",
            claims="",
            resource=[RESOURCE],
        )
        request = SimpleNamespace(resource=[])
        client = SimpleNamespace(client_id=CLIENT_ID)

        with patch.object(Grant.objects, "get", return_value=grant):
            self.assertTrue(validator.validate_code(CLIENT_ID, "code", client, request))

        self.assertEqual(request.resource, [RESOURCE])

    def test_refresh_request_inherits_its_original_resource(self):
        validator = UserClaimsValidator()
        request = SimpleNamespace(
            grant_type="refresh_token",
            refresh_token_instance=SimpleNamespace(resource=[RESOURCE]),
        )

        self.assertEqual(validator._set_inherited_resource(request), [RESOURCE])

    def test_jwt_authenticator_keeps_legacy_and_checks_resource_audience(self):
        authenticator = SSOJWTAuthentication()
        request = SimpleNamespace(build_absolute_uri=lambda: "https://api.example.com/v1/users/?page=1")

        self.assertTrue(authenticator._audience_matches(request, {"aud": [settings.OAUTH2_DEFAULT_AUDIENCE]}))
        self.assertTrue(authenticator._audience_matches(request, {"aud": ["https://api.example.com/v1/"]}))
        self.assertFalse(authenticator._audience_matches(request, {"aud": ["https://api.example.com/v2/"]}))
        self.assertFalse(authenticator._audience_matches(request, {"aud": ["https://evil.example.com/"]}))


class IntrospectionResourceTests(TestCase):
    def test_introspection_returns_stored_resource_as_audience(self):
        token_value = "test-resource-bound-access-token"
        access_token_model = get_access_token_model()
        access_token_model.objects.create(
            token=token_value,
            expires=timezone.now() + timedelta(minutes=5),
            scope=API_SCOPE,
            resource=[RESOURCE],
        )

        response = IntrospectTokenView.get_token_response(token_value)
        body = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertIs(body["active"], True)
        self.assertEqual(body["scope"], API_SCOPE)
        self.assertEqual(body["aud"], [RESOURCE])