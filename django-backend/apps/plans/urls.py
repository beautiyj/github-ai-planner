from django.urls import path
from . import views

urlpatterns = [
    # 목록/생성
    path("", views.PlanListView.as_view(), name="plan_list"),
    path("new/", views.PlanFormPageView.as_view(), name="plan_new"),

    # 수정 페이지
    path("edit/<int:plan_id>/", views.edit_plan_view, name="edit_plan"),

    # 상세/상세 페이지
    path("<int:plan_id>/page/", views.PlanPageView.as_view(), name="plan_page"),
    path("<int:plan_id>/summary/", views.SaveSummaryView.as_view(), name="save_summary"),
    path("<int:plan_id>/", views.PlanDetailView.as_view(), name="plan_detail"),
]