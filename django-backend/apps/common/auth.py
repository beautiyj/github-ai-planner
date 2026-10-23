from django.http import JsonResponse
from django.shortcuts import redirect


def get_current_github_user(request):
    return request.session.get("github_user") or {}


def get_guest_key(request):
    return request.session.get("guest_id")


def is_guest_user(request):
    return bool(get_current_github_user(request).get("is_guest"))


def login_required_redirect(view_func):
    def wrapper(request, *args, **kwargs):
        if not get_current_github_user(request):
            return redirect("/")
        return view_func(request, *args, **kwargs)
    return wrapper


def login_required_json(view_func):
    def wrapper(request, *args, **kwargs):
        if not get_current_github_user(request):
            return JsonResponse({"error": "로그인이 필요합니다."}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper

