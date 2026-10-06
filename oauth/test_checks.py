from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from oauth2_provider.models import AbstractApplication

from oauth.checks import check_oauth_signing_configuration


class OAuthSigningConfigurationCheckTests(SimpleTestCase):
    def run_check_for(self, algorithm, oidc_private_key="test-key"):
        application = SimpleNamespace(
            algorithm=algorithm,
            name="PocketBase Introspection",
            client_id="pocketbase",
        )
        with patch("oauth.checks.Application.objects.all", return_value=[application]):
            with override_settings(OAUTH2_PROVIDER={"OIDC_RSA_PRIVATE_KEY": oidc_private_key}):
                return check_oauth_signing_configuration(None)

    def test_no_oidc_algorithm_is_valid_for_non_oidc_clients(self):
        issues = self.run_check_for(AbstractApplication.NO_ALGORITHM)

        self.assertEqual(issues, [])

    def test_unknown_signing_algorithm_is_reported(self):
        issues = self.run_check_for("RS512")

        self.assertEqual([issue.id for issue in issues], ["oauth.E001"])

    def test_rs256_requires_configured_private_key(self):
        issues = self.run_check_for(AbstractApplication.RS256_ALGORITHM, oidc_private_key=None)

        self.assertEqual([issue.id for issue in issues], ["oauth.E002"])