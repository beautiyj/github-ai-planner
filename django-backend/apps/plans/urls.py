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
]