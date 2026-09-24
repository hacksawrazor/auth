from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
import json

#To-do: add proper health check and request scope.
def health(request):
    return JsonResponse({"status": "ok"})

@csrf_exempt
def login_view(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user = authenticate(
            request,
            username=data.get("username"),
            password=data.get("password")
        )
        if user:
            login(request, user)
            return JsonResponse({"status": "ok"})
        return JsonResponse({"error": "Invalid credentials"}, status=400)
    
@csrf_exempt
def logout_view(request):
    if request.method == "POST":
        logout(request)
        return JsonResponse({"status": "ok", "message": "logged out"})
    return JsonResponse({"error": "Invalid method"}, status=405)

def user_logout_view(request):
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, 'You have been logged out.')
    return redirect('/login/')


def user_login_view(request):
    if request.user.is_authenticated:
        return redirect('/dashboard/' if request.GET.get('next') is None else request.GET.get('next'))
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect('/dashboard/')
        messages.error(request, 'Invalid credentials.')
    return render(request, 'users/login.html')
