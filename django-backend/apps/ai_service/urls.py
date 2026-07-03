from django.urls import path
from . import views

urlpatterns = [
    path("generate-plan/", views.GeneratePlanView.as_view(), name="generate_plan"),
    path("daily-summary/", views.DailySummaryView.as_view(), name="daily_summary"),
]