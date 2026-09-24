from django.test import TestCase
from django.urls import resolve

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

    def test_user_signal_hook_imports(self):
        from users import signals
        self.assertTrue(hasattr(signals, 'add_user_to_token'))
