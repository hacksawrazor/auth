from django.test import TestCase, Client
from django.urls import reverse

class LoginViewBasicTests(TestCase):
    def test_login_url_resolves(self):
        self.assertEqual(reverse('user_login'), '/login/')

    def test_logout_url_resolves(self):
        self.assertEqual(reverse('user_logout'), '/logout/')

    def test_home_redirects_to_login(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/'))

    def test_login_renders_template(self):
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/login.html')
