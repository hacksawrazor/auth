from django.test import TestCase, Client

class HealthEndpointTests(TestCase):
    def test_health_status(self):
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('status', data)
