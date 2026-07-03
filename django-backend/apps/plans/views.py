import json
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .models import ProjectPlan, DailySummary

# 0406 커밋용주석 - 프로젝트 플랜 저장/조회/삭제 로직이랑 페이지 뷰 전체
"""
브라우저 (HTML)              백엔드 (views.py)
─────────────────────────────────────────────
버튼 클릭                →   GET / POST 요청 받음
fetch("/plans/", ...)    →   PlanListView.post() 실행
form 제출                →   DB에 저장
결과 받아서 화면에 표시  ←   JsonResponse 반환

urls.py   → 어떤 URL이 어떤 View로 갈지 지도 역할
views.py  → 실제 로직 처리 (DB 저장, AI 호출 등)
models.py → DB 테이블 구조 정의
templates → HTML 화면 (사용자가 보는 것)

사용자가 "플랜 저장" 버튼 클릭 (HTML)
→ JavaScript fetch("/plans/", {method: "POST"})
→ urls.py 가 PlanListView로 연결
→ views.py 의 post() 가 DB에 저장
→ {"success": True, "plan_id": 1} 반환
→ JS가 받아서 /plans/1/page/ 로 이동
→ views.py 의 PlanPageView.get() 이 HTML 렌더링
→ 사용자에게 플랜 상세 페이지 보여줌

"""


# 공통 데코레이터 ──────────────────────────────────────────────────────────────

# 로그인확인용 함수 (깃허브로그인용)
def login_required_redirect(view_func):
    # 로그인 안 된 경우 메인 페이지로 리다이렉트
    def wrapper(request, *args, **kwargs):
        if not request.session.get("github_user"):
            return redirect("/")
        return view_func(request, *args, **kwargs)

    return wrapper


# 로그인확인용 함수 (API 요청용)
def login_required_json(view_func):
    # 로그인 실패 JSON 401 반환
    def wrapper(request, *args, **kwargs):
        if not request.session.get("github_user"):
            return JsonResponse({"error": "로그인이 필요합니다."}, status=401)
        return view_func(request, *args, **kwargs)

    return wrapper


# GET / ─────────────────────────────────────────────────────────────
class MainView(View):
    """로그인 전: 랜딩 / 로그인 후: 대시보드 리다이렉트"""

    def get(self, request):
        github_user = request.session.get("github_user")
        if github_user:
            return redirect("/dashboard/")
        # github_user를 명시적으로 None으로 넘겨서 템플릿 user와 구분
        return render(request, "base/index.html", {"user": None})


# ── GET /dashboard/ ───────────────────────────────────────────
class DashboardView(View):
    """로그인 후 메인 대시보드"""

    # 클래스기반뷰 상태라서 @ 붙여줌 (원래 일반함수용으로 사용해야함)
    @method_decorator(login_required_redirect)
    def get(self, request):
        github_user = request.session.get("github_user")
        plans = ProjectPlan.objects.filter(github_login=github_user["login"])
        return render(request, "dashboard/index.html", {
            "user": github_user,
            "plans": plans,
        })


# ── GET /plans/new/ ───────────────────────────────────────────
class PlanFormPageView(View):
    """플랜 생성 폼 HTML 페이지"""

    @method_decorator(login_required_redirect)
    def get(self, request):
        github_user = request.session.get("github_user")
        return render(request, "plans/new.html", {"user": github_user})


# ── GET|POST /plans/ ──────────────────────────────────────────
@method_decorator(csrf_exempt, name="dispatch")
class PlanListView(View):

    @method_decorator(login_required_json)
    def get(self, request):
        """내 플랜 목록 JSON 반환"""
        github_user = request.session.get("github_user")
        plans = ProjectPlan.objects.filter(
            github_login=github_user["login"]
        ).values("id", "title", "purposes", "date_start", "date_end", "created_at")
        return JsonResponse({"success": True, "plans": list(plans)})

    @method_decorator(login_required_json)
    def post(self, request):
        """AI 생성 플랜 DB 저장"""
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "잘못된 JSON 형식입니다."}, status=400)

        github_user = request.session.get("github_user")
        plan = ProjectPlan.objects.create(
            github_login=github_user["login"],
            title=body.get("title", ""),
            purposes=body.get("purposes", []),
            date_start=body.get("date_start") or None,
            date_end=body.get("date_end") or None,
            skills=body.get("skills", []),
            features=body.get("features", ""),
            repo_url=body.get("repo_url", ""),
            ai_plan=body.get("ai_plan", {}),
        )
        return JsonResponse({
            "success": True,
            "plan_id": plan.id,
            "message": "플랜이 저장되었습니다.",
        }, status=201)


# ── GET|DELETE /plans/<id>/ ───────────────────────────────────
@method_decorator(csrf_exempt, name="dispatch")
class PlanDetailView(View):

    @method_decorator(login_required_json)
    def get(self, request, plan_id):
        """플랜 상세 JSON 반환"""
        github_user = request.session.get("github_user")
        plan = get_object_or_404(
            ProjectPlan, id=plan_id, github_login=github_user["login"]
        )
        summaries = list(plan.daily_summaries.values(
            "date", "ai_summary", "mood", "progress_percent", "highlight"
        )[:7])
        return JsonResponse({
            "success": True,
            "plan": {
                "id": plan.id,
                "title": plan.title,
                "purposes": plan.purposes,
                "date_start": str(plan.date_start) if plan.date_start else None,
                "date_end": str(plan.date_end) if plan.date_end else None,
                "skills": plan.skills,
                "features": plan.features,
                "repo_url": plan.repo_url,
                "ai_plan": plan.ai_plan,
                "created_at": str(plan.created_at),
            },
            "recent_summaries": summaries,
        })

    @method_decorator(login_required_json)
    def delete(self, request, plan_id):
        """플랜 삭제"""
        github_user = request.session.get("github_user")
        plan = get_object_or_404(
            ProjectPlan, id=plan_id, github_login=github_user["login"]
        )
        plan.delete()
        return JsonResponse({"success": True, "message": "플랜이 삭제되었습니다."})


# ── GET /plans/<id>/page/ ─────────────────────────────────────
class PlanPageView(View):
    """플랜 상세 HTML 페이지"""

    @method_decorator(login_required_redirect)
    def get(self, request, plan_id):
        github_user = request.session.get("github_user")
        plan = get_object_or_404(
            ProjectPlan, id=plan_id, github_login=github_user["login"]
        )
        summaries = plan.daily_summaries.all()[:7]
        return render(request, "plans/detail.html", {
            "user": github_user,
            "plan": plan,
            "summaries": summaries,
        })


# ── POST /plans/<id>/summary/ ─────────────────────────────────
@method_decorator(csrf_exempt, name="dispatch")
class SaveSummaryView(View):
    """일일 요약 저장 — 같은 날짜면 업데이트, 없으면 생성"""

    @method_decorator(login_required_json)
    def post(self, request, plan_id):
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "잘못된 JSON 형식입니다."}, status=400)

        github_user = request.session.get("github_user")
        plan = get_object_or_404(
            ProjectPlan, id=plan_id, github_login=github_user["login"]
        )
        summary_data = body.get("summary", {})

        obj, created = DailySummary.objects.update_or_create(
            plan=plan,
            date=body.get("date"),
            defaults={
                "commits": body.get("commits", []),
                "ai_summary": summary_data.get("summary", ""),
                "advice": summary_data.get("advice", ""),
                "mood": summary_data.get("mood", "good"),
                "progress_percent": summary_data.get("progress_percent", 0),
                "highlight": summary_data.get("highlight", "") or "",
            },
        )
        return JsonResponse({
            "success": True,
            "created": created,
            "message": "요약이 저장되었습니다.",
        })
