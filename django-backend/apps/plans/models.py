from django.db import models

# models.py : DB 엔티티 정의 목적 파일


class ProjectPlan(models.Model):
    # GitHub 유저명
    github_login = models.CharField(max_length=100)

    # 0702추가 - 게스트에서 로그인회원가입 시 기억하는 용도: 게스트 상태에서 로그인으로 전환할 때 식별할 임시 세션 키
    guest_session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)

    # 프로젝트 기본 정보
    title = models.CharField(max_length=200)
    purposes = models.JSONField(default=list)
    date_start = models.DateField(null=True, blank=True)
    date_end = models.DateField(null=True, blank=True)
    skills = models.JSONField(default=list)
    features = models.TextField()
    repo_url = models.CharField(max_length=300, blank=True)

    # AI가 생성한 플랜 전체를 JSON으로 저장
    ai_plan = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "project_plans"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.github_login} - {self.title}"


class DailySummary(models.Model):
    #일일 커밋 요약 테이블

    plan = models.ForeignKey(
        ProjectPlan,
        on_delete=models.CASCADE,
        related_name="daily_summaries"
    )

    date = models.DateField()
    commits = models.JSONField(default=list)
    ai_summary = models.TextField()
    advice = models.TextField(blank=True)
    mood = models.CharField(max_length=20)
    progress_percent = models.IntegerField(default=0)
    highlight = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "daily_summaries"
        unique_together = ["plan", "date"]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.plan.title} - {self.date}"