from django.contrib import admin
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from oauth2_provider.models import get_application_model

from oauth.admin import OAuthApplicationAdmin, OAuthClientPolicyInline, OAuthResourcePolicyInline
from oauth.forms import OAuthClientPolicyForm, OAuthResourcePolicyForm
from oauth.models import OAuthClientPolicy, OAuthResourcePolicy


RESOURCE = "https://api.example.com/"
SCOPES = {
    "openid": "OpenID Connect scope",
    "api:read": "Read API data",
    "api:write": "Write API data",
}


@override_settings(
    OAUTH2_PROVIDER={"SCOPES": SCOPES},
    OAUTH2_API_SCOPES={"api:read": "Read API data", "api:write": "Write API data"},
)
class OAuthPolicyAdminTests(TestCase):
    def setUp(self):
        self.application = get_application_model().objects.create(
            client_id="admin-test-client",
            name="Admin test client",
            client_type="confidential",
            authorization_grant_type="authorization-code",
            redirect_uris="https://client.example.com/callback",
        )

    def test_application_admin_has_policy_inlines(self):
        inlines = [inline.model for inline in OAuthApplicationAdmin.inlines]

        self.assertEqual(inlines, [OAuthClientPolicy, OAuthResourcePolicy])
        self.assertIn(get_application_model(), admin.site._registry)
        self.assertIsInstance(admin.site._registry[get_application_model()], OAuthApplicationAdmin)
        self.assertEqual(OAuthClientPolicyInline.max_num, 1)
        self.assertIs(OAuthResourcePolicyInline.model, OAuthResourcePolicy)

    def test_client_defaults_form_saves_selected_registered_scopes(self):
        form = OAuthClientPolicyForm(data={"default_scopes": ["openid", "api:read"]})
        self.assertTrue(form.is_valid(), form.errors)

        policy = form.save(commit=False)
        policy.application = self.application
        policy.save()

        self.assertEqual(policy.default_scopes, ["openid", "api:read"])

    def test_resource_form_rejects_unregistered_scopes(self):
        form = OAuthResourcePolicyForm(
            data={"resource_uri": RESOURCE, "scopes": ["api:missing"], "is_default": "on"}
        )

        self.assertFalse(form.is_valid())
        self.assertIn("scopes", form.errors)

    def test_resource_form_rejects_non_https_audience(self):
        form = OAuthResourcePolicyForm(
            data={"resource_uri": "http://api.example.com/", "scopes": ["api:read"]}
        )

        self.assertFalse(form.is_valid())
        self.assertIn("resource_uri", form.errors)

    def test_resource_scope_selector_contains_only_api_scopes(self):
        form = OAuthResourcePolicyForm()

        self.assertEqual(
            [scope for scope, _label in form.fields["scopes"].choices],
            ["api:read", "api:write"],
        )

    def test_resource_form_saves_https_audience_and_scopes(self):
        form = OAuthResourcePolicyForm(
            data={"resource_uri": RESOURCE, "scopes": ["api:read"], "is_default": "on"}
        )
        self.assertTrue(form.is_valid(), form.errors)

        policy = form.save(commit=False)
        policy.application = self.application
        policy.save()

        self.assertEqual(policy.resource_uri, RESOURCE)
        self.assertEqual(policy.scopes, ["api:read"])
        self.assertTrue(policy.is_default)

    def test_database_rejects_multiple_default_audiences_for_one_client(self):
        OAuthResourcePolicy.objects.create(
            application=self.application,
            resource_uri=RESOURCE,
            scopes=["api:read"],
            is_default=True,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                OAuthResourcePolicy.objects.create(
                    application=self.application,
                    resource_uri="https://other.example.com/",
                    scopes=["api:read"],
                    is_default=True,
                )