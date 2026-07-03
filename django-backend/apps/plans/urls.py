from django.urls import path
from . import views

urlpatterns = [
    # HTML 페이지
    path("new/",                   views.PlanFormPageView.as_view(), name="plan_new"),
    path("<int:plan_id>/page/",    views.PlanPageView.as_view(),     name="plan_page"),

    # JSON API
    path("",                       views.PlanListView.as_view(),     name="plan_list"),
    path("<int:plan_id>/",         views.PlanDetailView.as_view(),   name="plan_detail"),
    path("<int:plan_id>/summary/", views.SaveSummaryView.as_view(),  name="save_summary"),

    # 0703
    # 수정 페이지 호출: /plans/edit/1/
    path('edit/<int:plan_id>/', views.edit_plan_view, name='edit_plan'),
    # 플랜 수정/삭제 처리 API: /plans/1/
    path('<int:plan_id>/', views.plan_detail_api, name='plan_api'),
]