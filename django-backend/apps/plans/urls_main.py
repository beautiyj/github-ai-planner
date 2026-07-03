from django.urls import path
from . import views

#0406 커밋용 주석 - 루트(/) 와 /dashboard/ URL 등록

urlpatterns = [
    path("", views.MainView.as_view(), name="main"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
]