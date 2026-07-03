import json
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q  # 👈 게스트용 오어(OR) 조회를 위해 추가

from .models import ProjectPlan, DailySummary, ProjectPlan
from apps.ai_service.prompts import build_plan_prompt
from apps.ai_service.ai_provider import call_ai

#0703 수정 Q(guest_session_key=request.session.session_key)
#  -> 모두 Q(guest_session_key=request.session.get("guest_id")) 로 변경

# 공통 데코레이터 ──────────────────────────────────────────────────────────────

def login_required_redirect(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get("github_user"):
            return redirect("/")
        return view_func(request, *args, **kwargs)

    return wrapper


def login_required_json(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get("github_user"):
            return JsonResponse({"error": "로그인이 필요합니다."}, status=401)
        return view_func(request, *args, **kwargs)

    return wrapper


# GET / ─────────────────────────────────────────────────────────────
class MainView(View):
    def get(self, request):
        github_user = request.session.get("github_user")
        if github_user:
            return redirect("/dashboard/")
        return render(request, "base/index.html", {"user": None})


# ── GET /dashboard/ ───────────────────────────────────────────
# 0703수정 - DashboardView, PlanListView(get) 등 Q 객체 조회 조건 수정
class DashboardView(View):
    """로그인 후 또는 게스트용 메인 대시보드"""

    @method_decorator(login_required_redirect)
    def get(self, request):
        github_user = request.session.get("github_user")

        # 💡 request.session.session_key 자리를 request.session.get("guest_id")로 수정!
        plans = ProjectPlan.objects.filter(
            Q(github_login=github_user["login"]) |
            Q(guest_session_key=request.session.get("guest_id"))
        )
        return render(request, "dashboard/index.html", {
            "user": github_user,
            "plans": plans,
        })


# ── GET /plans/new/ ───────────────────────────────────────────
class PlanFormPageView(View):
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

        # 💡 [수정] 목록 조회시에도 내 계정이거나 내 세션 키인 데이터를 필터링
        plans = ProjectPlan.objects.filter(
            Q(github_login=github_user["login"]) |
            Q(guest_session_key=request.session.get("guest_id"))
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
        is_guest = github_user.get("is_guest", False) if github_user else False

        # # 💡 [수정] 게스트 상태라면 장고가 무조건 세션 키를 유지하도록 확인
        # if is_guest and not request.session.session_key:
        #     request.session.create()

        # 💡 [수정] 모델의 guest_session_key 필드에 세션 내 고정된 guest_id를 저장합니다. 세션키->아이디로 수정!
        plan = ProjectPlan.objects.create(
            github_login=github_user["login"],
            guest_session_key=request.session.get("guest_id") if is_guest else None,  # 👈 수정!
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

        # 💡 [수정] 내 소유의 플랜이거나 내 임시 세션용 플랜인지 함께 판단
        plan = get_object_or_404(
            ProjectPlan,
            Q(id=plan_id) & (Q(github_login=github_user["login"]) | Q(guest_session_key=request.session.get("guest_id")))
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
    def put(self, request, plan_id):
        """플랜 수정 로직"""
        body = json.loads(request.body)
        github_user = request.session.get("github_user")

        # 권한 확인: 내 것만 수정 가능
        plan = get_object_or_404(ProjectPlan, id=plan_id, github_login=github_user["login"])

        plan.title = body.get("title", plan.title)
        plan.features = body.get("features", plan.features)

        # 0703 AI 수정 요청이 있을 경우 AI 호출(기존마일스톤기억하기)
        modify_request = body.get("modify_request")  # 프론트엔드에서 보낸 수정 요구사항
        if modify_request:
            # 프롬프트 데이터 구성
            prompt_data = body.copy()
            prompt_data["existing_plan"] = plan.ai_plan  # 기존 마일스톤 유지용 데이터

            # 프롬프트 생성 및 AI 서비스 호출 (ai_service는 별도로 구현하신 함수)
            prompt = build_plan_prompt(prompt_data)
            new_ai_result = call_ai(prompt)  # AI에게 수정된 결과 받기

            # 새로운 AI 결과 저장
            plan.ai_plan = new_ai_result
        plan.save()

        return JsonResponse({"success": True, "ai_plan": plan.ai_plan})

    @method_decorator(login_required_json)
    def delete(self, request, plan_id):
        """플랜 삭제"""
        github_user = request.session.get("github_user")
        plan = get_object_or_404(
            ProjectPlan,
            Q(id=plan_id) & (Q(github_login=github_user["login"]) | Q(guest_session_key=request.session.get("guest_id")))
        )
        plan.delete()
        return JsonResponse({"success": True, "message": "플랜이 삭제되었습니다."})

# 0703 로그인 사용자 플랜 수정 시 데이터 기억하는 용도
class PlanEditPageView(View):
    """기존 플랜 데이터를 폼에 채워넣어 보여주는 페이지"""

    @method_decorator(login_required_redirect)
    def get(self, request, plan_id):
        github_user = request.session.get("github_user")
        plan = get_object_or_404(ProjectPlan, id=plan_id, github_login=github_user["login"])

        # detail.html과 다르게 new.html처럼 폼이 있는 페이지로 렌더링
        return render(request, "plans/new.html", {
            "user": github_user,
            "plan": plan,  # 이 변수를 통해 HTML에서 기존 값을 불러옵니다
            "is_edit_mode": True  # 수정 모드임을 알림
        })

# ── GET /plans/<id>/page/ ─────────────────────────────────────
class PlanPageView(View):
    """플랜 상세 HTML 페이지"""

    @method_decorator(login_required_redirect)
    def get(self, request, plan_id):
        github_user = request.session.get("github_user")
        plan = get_object_or_404(
            ProjectPlan,
            Q(id=plan_id) & (Q(github_login=github_user["login"]) | Q(guest_session_key=request.session.get("guest_id")))
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
            ProjectPlan,
            Q(id=plan_id) & (Q(github_login=github_user["login"]) | Q(guest_session_key=request.session.get("guest_id")))
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


# 1. 수정 페이지 렌더링 뷰
def edit_plan_view(request, plan_id):
    plan = get_object_or_404(ProjectPlan, id=plan_id)
    # 기존 new.html을 수정 페이지로 재사용 (context에 plan 객체 전달)
    return render(request, 'plans/new.html', {'plan': plan})


# 2. 플랜 수정(PUT) 및 삭제(DELETE) 처리 API 뷰
def plan_detail_api(request, plan_id):
    plan = get_object_or_404(ProjectPlan, id=plan_id)

    if request.method == 'PUT':
        # 데이터 수정 로직 (JSON 파싱 후 저장)
        data = json.loads(request.body)
        plan.title = data.get('title')
        # ... 나머지 필드 업데이트 ...
        plan.save()
        return JsonResponse({'success': True})

    elif request.method == 'DELETE':
        # 플랜 삭제 로직
        plan.delete()
        return JsonResponse({'success': True})

    return JsonResponse({'error': 'Method not allowed'}, status=405)