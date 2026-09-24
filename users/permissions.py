from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly

class IsStaffOrReadOnly(IsAuthenticatedOrReadOnly):
    def has_permission(self, request, view):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return super().has_permission(request, view)
        return request.user and request.user.is_authenticated and request.user.is_staff
