from django.test import TestCase, Client
from django.urls import reverse
from users.models import User

class LoginSessionFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass', email='t@t.com')

    def test_login_post_valid_redirects(self):
        # Uses existing admin superuser (admin/admin per README docs)
        response = self.client.post('/login/', {'username': 'testuser', 'password': 'testpass', 'next': '/dashboard/'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/dashboard/', response.url)

    def test_login_post_invalid_shows_error(self):
        response = self.client.post('/login/', {'username': 'bad', 'password': 'bad'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid credentials')

    def test_login_get_renders_form(self):
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign in')

    def test_logout_redirects_to_login(self):
        # Login first to have session
        self.client.post('/login/', {'username': 'admin', 'password': 'admin'})
        response = self.client.get('/logout/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
