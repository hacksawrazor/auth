from datetime import timedelta
import json
from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase, override_settings
from django.utils import timezone
from oauth2_provider.models import get_access_token_model, get_application_model
from oauth2_provider.oauth2_validators import Grant
from oauth2_provider.views.introspect import IntrospectTokenView

from oauth.authentication import SSOJWTAuthentication
from oauth.models import OAuthClientPolicy, OAuthResourcePolicy
from oauth.jwt_tokens import jwt_access_token_generator
from oauth.validators import UserClaimsValidator

RESOURCE = "https://pocketbase.example.com/"
ENV_RESOURCE = "https://legacy-api.example.com/"
API_SCOPE = "pocketbase:access"
OTHER_API_SCOPE = "reports:access"
CLIENT_ID = "nginx-gateway"

RESOURCE_SETTINGS = {
    "OAUTH2_API_SCOPES": {
        API_SCOPE: "Access to the PocketBase API",
        OTHER_API_SCOPE: "Access to reports API",
    },
    "OAUTH2_RESOURCE_POLICIES": {CLIENT_ID: {ENV_RESOURCE: [API_SCOPE]}},
    "OAUTH2_CLIENT_DEFAULTS": {CLIENT_ID: {"resources": [ENV_RESOURCE], "scopes": [API_SCOPE]}},
    "OAUTH2_DEFAULT_AUDIENCE": "legacy-resource",
    "OAUTH2_DEFAULT_SCOPES": ["openid", "email", "profile"],
    "OAUTH2_PROVIDER": {
        **settings.OAUTH2_PROVIDER,
        "SCOPES": {
            **settings.OAUTH2_PROVIDER["SCOPES"],
            API_SCOPE: "Access to the PocketBase API",
            OTHER_API_SCOPE: "Access to reports API",
        },
    },
}


class ResourceAudienceTests(TestCase):
    def setUp(self):
        self.application = get_application_model().objects.create(
            client_id=CLIENT_ID,
            name="Test OAuth client",
            client_type="confidential",
            authorization_grant_type="authorization-code",
            redirect_uris="https://client.example.com/callback",
        )
        self.legacy_application = get_application_model().objects.create(
            client_id="existing-client",
            name="Existing client",
            client_type="confidential",
            authorization_grant_type="authorization-code",
            redirect_uris="https://client.example.com/legacy-callback",
        )

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
        client = self.application

        allowed = SimpleNamespace(client=client, resource=[ENV_RESOURCE])
        denied = SimpleNamespace(client=client, resource=["https://other.example.com/"])
        unconfigured_client = get_application_model().objects.create(
            client_id="unconfigured-client",
            name="Unconfigured client",
            client_type="confidential",
            authorization_grant_type="authorization-code",
            redirect_uris="https://client.example.com/other-callback",
        )
        unbound = SimpleNamespace(client=unconfigured_client, resource=[])

        self.assertTrue(validator.validate_scopes(CLIENT_ID, [API_SCOPE], client, allowed))
        self.assertFalse(validator.validate_scopes(CLIENT_ID, [API_SCOPE], client, denied))
        self.assertFalse(
            validator.validate_scopes("unconfigured-client", [API_SCOPE], unconfigured_client, unbound)
        )

    @override_settings(**RESOURCE_SETTINGS)
    def test_legacy_scopes_remain_valid_without_resource(self):
        validator = UserClaimsValidator()
        client = self.legacy_application
        request = SimpleNamespace(client=client, resource=[])

        self.assertTrue(
            validator.validate_scopes("existing-client", ["openid", "email"], client, request)
        )

    @override_settings(**RESOURCE_SETTINGS)
    def test_client_defaults_supply_resource_and_scopes(self):
        validator = UserClaimsValidator()
        client = self.application
        OAuthClientPolicy.objects.create(application=client, default_scopes=[API_SCOPE])
        OAuthResourcePolicy.objects.create(
            application=client,
            resource_uri=RESOURCE,
            scopes=[API_SCOPE],
            is_default=True,
        )
        request = SimpleNamespace(client=client, resource=[])

        self.assertEqual(validator.get_default_scopes(CLIENT_ID, request), [API_SCOPE])
        self.assertEqual(request.resource, [RESOURCE])

    @override_settings(**RESOURCE_SETTINGS)
    def test_admin_policy_overrides_environment_policy(self):
        validator = UserClaimsValidator()
        OAuthClientPolicy.objects.create(application=self.application, default_scopes=[API_SCOPE])
        OAuthResourcePolicy.objects.create(
            application=self.application,
            resource_uri=RESOURCE,
            scopes=[API_SCOPE],
            is_default=True,
        )
        request = SimpleNamespace(client=self.application, resource=[RESOURCE])

        self.assertTrue(validator.validate_scopes(CLIENT_ID, [API_SCOPE], self.application, request))
        self.assertFalse(
            validator.validate_scopes(CLIENT_ID, [OTHER_API_SCOPE], self.application, request)
        )

    @override_settings(OAUTH2_DEFAULT_SCOPES=["openid", "profile"], OAUTH2_CLIENT_DEFAULTS={})
    def test_global_default_scopes_are_configurable(self):
        validator = UserClaimsValidator()
        client = self.legacy_application
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
        client = self.application

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