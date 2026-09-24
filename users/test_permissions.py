from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from users.permissions import IsStaffOrReadOnly

User = get_user_model()

class PermissionsTests(TestCase):
    def test_staff_or_readonly(self):
        perm = IsStaffOrReadOnly()
        request = self.client.get('/').wsgi_request
        request.method = 'GET'
        self.assertTrue(perm.has_permission(request, None))
