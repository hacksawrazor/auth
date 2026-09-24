from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib import messages

# To-do: add proper health check and request scope.
def health(request):
    from django.db import connection
    from django.conf import settings
    db_ok = False
    oidc_ok = False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            db_ok = True
    except Exception:
        pass
    try:
        # Verify OIDC private key load path exists / settings configured
        from pathlib import Path
        pem_path = settings.BASE_DIR / 'oidc_private.pem'
        if settings.OAUTH2_PROVIDER.get('OIDC_RSA_PRIVATE_KEY') is not None:
            oidc_ok = True
        elif settings.OAUTH2_PROVIDER.get('OIDC_ISS_ENDPOINT') and pem_path.exists():
            oidc_ok = True
        else:
            oidc_ok = False
    except Exception:
        oidc_ok = False
    status = "ok" if (db_ok and oidc_ok) else "degraded"
    return JsonResponse({
        "status": status,
        "db": db_ok,
        "oidc_config": oidc_ok,
    })

def user_logout_view(request):
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, 'You have been logged out.')
    return redirect('/login/')


def user_login_view(request):
    if request.user.is_authenticated:
        next_url = request.GET.get('next')
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return render(request, 'users/login_success.html')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return render(request, 'users/login_success.html')
        messages.error(request, 'Invalid credentials.')
    return render(request, 'users/login.html', {'next': request.GET.get('next') or ''})
