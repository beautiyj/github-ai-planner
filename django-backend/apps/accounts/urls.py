from django.urls import path
from . import views

# Controller (Mapping) 역할 - urls.py
# URL 주소를 매핑하여 특정 뷰(컨트롤러)로 던져주는 라우터 역할

urlpatterns = [
    path("login/", views.GithubLoginView.as_view(), name="github_login"),
    path("github/callback/", views.GithubCallbackView.as_view(), name="github_callback"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("me/", views.MeView.as_view(), name="me"),

    # 테스트용 로그인 API (개발 중에만 사용, 나중에 삭제 예정)
    path("test-login/", views.TestLoginView.as_view(), name="test_login"),

     # 게스트 로그인
    path("guest-login/", views.GuestLoginView.as_view(), name="guest_login"),
]