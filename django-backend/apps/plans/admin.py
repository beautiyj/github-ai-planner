from django.contrib import admin
from .models import ProjectPlan, DailySummary

# 0406 커밋용주석 - 관리자페이지 설정
# admin.py : 장고 내장 관리자 페이지 설정 파일

@admin.register(ProjectPlan)
class ProjectPlanAdmin(admin.ModelAdmin):
    list_display = ("id", "github_login", "title", "date_start", "date_end", "created_at")
    list_filter = ("github_login",)
    search_fields = ("title", "github_login")
    readonly_fields = ("created_at", "updated_at")


@admin.register(DailySummary)
class DailySummaryAdmin(admin.ModelAdmin):
    list_display = ("id", "plan", "date", "mood", "progress_percent", "created_at")
    list_filter = ("mood",)
    search_fields = ("plan__title",)
    readonly_fields = ("created_at",)