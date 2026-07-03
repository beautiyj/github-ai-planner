import os
import requests
from django.shortcuts import redirect
from django.http import JsonResponse
from django.views import View
from apps.plans.models import ProjectPlan  # 👈 플랜 데이터 조작을 위해 임포트 추가


# 0406 커밋용주석 - GitHub OAuth 로그인/로그아웃 처리
# 0406 코드만 작성, 이후 깃허브 api 발급 필요

# 0409 테스트용 로그인 로직 추가
class TestLoginView(View):
    def get(self, request):
        request.session["github_access_token"] = "test-token-12345"
        request.session["github_user"] = {
            "login": "test-user",
            "name": "테스트 유저",
            "avatar_url": "",
            "email": "test@test.com",
        }
        return redirect("/dashboard/")


# 0629 깃허브용 테스트 로그인 로직 추가
class GithubLoginView(View):
    """GitHub OAuth 시작점 — 클릭하면 GitHub 인증 페이지로 이동"""

    def get(self, request):
        client_id = os.getenv("GITHUB_CLIENT_ID")
        scope = "read:user user:email repo"
        github_auth_url = (
            f"https://github.com/login/oauth/authorize"
            f"?client_id={client_id}&scope={scope}"
        )
        return redirect(github_auth_url)


class GithubCallbackView(View):
    """-------GitHub 인증 완료 후 돌아오는 URL — code → access_token 교환--------"""

    def get(self, request):
        code = request.GET.get("code")
        if not code:
            return redirect("/?error=oauth_failed")

        # 1. 덮어쓰기 전, 기존 게스트 세션 정보 및 키 '확실하게' 백업 ------------------
        current_user = request.session.get("github_user") or {}
        was_guest = current_user.get("is_guest", False)
        old_session_key = request.session.session_key  # 스크린샷 1번 시점의 키

        # code → access_token 교환하기 ---------------------------------------
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

        # access_token으로 유저 정보 조회-------------------------------------
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

        # 세션에 새 유저 정보 저장하기 ----------------------------------------------------
        request.session["github_access_token"] = access_token
        request.session["github_user"] = {
            "login": login_id,
            "name": github_user.get("name"),
            "avatar_url": github_user.get("avatar_url"),
            "email": github_user.get("email"),
            "is_guest": False,  # 게스트 탈출 마킹
        }

        # 2. 🎉 게스트 플랜 데이터 마이그레이션 실행(게스트상태에서 깃허브 로그인 시 플랜 백업) ----------------------
        if was_guest and old_session_key:
            # 기존 게스트 세션 키로 저장되어 있던 플랜들을 전부 타겟팅
            guest_plans = ProjectPlan.objects.filter(guest_session_key=old_session_key)
            if guest_plans.exists():
                # 주인을 깃허브 로그인한 계정으로 바꾸고 게스트 임시 키는 초기화!
                guest_plans.update(
                    github_login=login_id,
                    guest_session_key=None
                )

        return redirect("/dashboard/")


class LogoutView(View):
    """-----------세션 삭제 후 메인으로 이동하기------------"""

    def get(self, request):
        request.session.flush()
        return redirect("/")


class MeView(View):
    """------------현재 로그인한 유저 정보 반환 (JSON)------------"""

    def get(self, request):
        github_user = request.session.get("github_user")
        if not github_user:
            return JsonResponse({"error": "로그인이 필요합니다."}, status=401)
        return JsonResponse({"success": True, "user": github_user})


# 0629 게스트용 로그인 로직 추가
class GuestLoginView(View):
    """게스트 로그인 — GitHub 계정 없이 둘러보기용"""

    def get(self, request):
        # 장고에게 확실하게 세션 아이디(session_key)를 발급받도록 강제 처리
        if not request.session.session_key:
            request.session.create()

        request.session["github_access_token"] = None
        request.session["github_user"] = {
            "login": "guest",
            "name": "게스트",
            "avatar_url": "",
            "email": "",
            "is_guest": True,
        }
        return redirect("/dashboard/")