import os
import uuid
import requests
from django.shortcuts import redirect
from django.http import JsonResponse
from django.views import View

from apps.plans.models import ProjectPlan


class TestLoginView(View):
    def get(self, request):
        request.session["github_access_token"] = "test-token-12345"
        request.session["github_user"] = {
            "login": "test-user",
            "name": "테스트 유저",
            "avatar_url": "",
            "email": "test@test.com",
            "is_guest": False,
        }
        return redirect("/dashboard/")


class GithubLoginView(View):
    def get(self, request):
        client_id = os.getenv("GITHUB_CLIENT_ID")
        scope = "read:user user:email repo"
        github_auth_url = (
            f"https://github.com/login/oauth/authorize"
            f"?client_id={client_id}&scope={scope}"
        )
        return redirect(github_auth_url)


class GithubCallbackView(View):
    def get(self, request):
        code = request.GET.get("code")
        if not code:
            return redirect("/?error=oauth_failed")

        current_user = request.session.get("github_user") or {}
        was_guest = current_user.get("is_guest", False)
        old_guest_id = request.session.get("guest_id")

        token_response = requests.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": os.getenv("GITHUB_CLIENT_ID"),
                "client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
                "code": code,
            },
            headers={"Accept": "application/json"},
            timeout=10,
        )
        token_data = token_response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            return redirect("/?error=token_failed")

        user_response = requests.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=10,
        )
        github_user = user_response.json()
        login_id = github_user.get("login")

        request.session["github_access_token"] = access_token
        request.session["github_user"] = {
            "login": login_id,
            "name": github_user.get("name"),
            "avatar_url": github_user.get("avatar_url"),
            "email": github_user.get("email"),
            "is_guest": False,
        }

        if was_guest and old_guest_id:
            guest_plans = ProjectPlan.objects.filter(guest_session_key=old_guest_id)
            if guest_plans.exists():
                guest_plans.update(
                    github_login=login_id,
                    guest_session_key=None,
                )

        return redirect("/dashboard/")


class LogoutView(View):
    def get(self, request):
        request.session.flush()
        return redirect("/")


class MeView(View):
    def get(self, request):
        github_user = request.session.get("github_user")
        if not github_user:
            return JsonResponse({"error": "로그인이 필요합니다."}, status=401)
        return JsonResponse({"success": True, "user": github_user})


class GuestLoginView(View):
    def get(self, request):
        if not request.session.session_key:
            request.session.create()

        if "guest_id" not in request.session:
            request.session["guest_id"] = f"guest_{uuid.uuid4().hex[:12]}"

        request.session["github_access_token"] = None
        request.session["github_user"] = {
            "login": "guest",
            "name": "게스트",
            "avatar_url": "",
            "email": "",
            "is_guest": True,
        }
        return redirect("/dashboard/")