from django.conf import settings
from django.test import SimpleTestCase

from oauth.scope_catalog import API_SCOPE_CATALOG, DEFAULT_SCOPE_NAMES, SCOPE_CATALOG


class OAuthScopeCatalogTests(SimpleTestCase):
    def test_provider_registers_every_catalog_scope(self):
        self.assertEqual(settings.OAUTH2_PROVIDER["SCOPES"], SCOPE_CATALOG)

    def test_api_scope_catalog_is_registered_for_resource_policies(self):
        self.assertEqual(settings.OAUTH2_API_SCOPES, API_SCOPE_CATALOG)
        self.assertTrue(set(API_SCOPE_CATALOG).issubset(SCOPE_CATALOG))

    def test_global_default_scopes_are_catalogued(self):
        self.assertEqual(settings.OAUTH2_DEFAULT_SCOPES, list(DEFAULT_SCOPE_NAMES))
        self.assertTrue(set(DEFAULT_SCOPE_NAMES).issubset(SCOPE_CATALOG))