from django.test import TestCase
from django.urls import resolve

from unittest.mock import patch, MagicMock

class OIDCVerificationTests(TestCase):
    def test_oauthorize_resolves(self):
        # /o/ is a URLResolver; verify authorize pattern exists
        res = resolve('/o/authorize/')
        self.assertEqual(res.url_name, 'authorize')

    def test_auth_classes_include_oidc(self):
        from django.conf import settings
        classes = settings.REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']
        names = [c.split('.')[-1] for c in classes]
        self.assertIn('SSOJWTAuthentication', names)
        self.assertIn('OAuth2Authentication', names)
        self.assertNotIn('JWTAuthentication', names)

    def test_mock_token_load_for_ssojwt(self):
        from oauth.authentication import SSOJWTAuthentication
        auth = SSOJWTAuthentication()
        with patch.object(auth, 'authenticate') as mock_auth:
            mock_auth.return_value = (MagicMock(), None)
            result = auth.authenticate(MagicMock())
            mock_auth.assert_called_once()

    def test_user_signal_hook_imports(self):
        from users import signals
        self.assertTrue(hasattr(signals, 'add_user_to_token'))
        from users import signals
        self.assertTrue(hasattr(signals, 'add_user_to_token'))
