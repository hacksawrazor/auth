from django.test import TestCase, Client
from django.contrib.auth import get_user_model

User = get_user_model()

class HomeViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='t', password='tpass')

    def test_home_redirect_for_anonymous(self):
        response = self.client.get('/home/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_home_renders_for_auth(self):
        self.client.login(username='t', password='tpass')
        response = self.client.get('/home/')
        self.assertEqual(response.status_code, 200)
