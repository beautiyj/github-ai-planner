from django.contrib import admin
from django.urls import path, include

# 각 패키지의 urls.py를 include하여 프로젝트 전체 URL 매핑을 구성(최상위 config/urls.py와 매핑하는 역할)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("plans/", include("apps.plans.urls")),
    path("github/", include("apps.github_api.urls")),
    path("ai/", include("apps.ai_service.urls")),
    path("", include("apps.plans.urls_main")),
]