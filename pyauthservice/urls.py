from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from oauth2_provider import urls as oauth2_urls
from users import urls as users_urls
from .views import health, user_login_view, user_logout_view

urlpatterns = [
    path('', RedirectView.as_view(url='/login/', permanent=False), name='home'),
    path('admin/', admin.site.urls),
    path('o/', include(oauth2_urls)),
    path('api/', include(users_urls)),
    path('logout/', user_logout_view, name='user_logout'),
    path('login/', user_login_view, name='user_login'),
    from pyauthservice import views
    path('home/', views.home_view, name='user_home'),
    path('health/', health, name='health'),
]

admin.site.site_header = 'Auth Service Administration'
admin.site.index_title = 'User Management'
admin.site.site_title = 'Auth Service Admin'
