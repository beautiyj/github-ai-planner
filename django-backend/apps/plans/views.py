import json
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q

from .models import ProjectPlan, DailySummary
from apps.ai_service.prompts import build_plan_prompt
from apps.ai_service.ai_provider import call_ai


def get_current_github_user(request):
    return request.session.get("github_user") or {}


def get_guest_key(request):
    return request.session.get("guest_id")


def is_guest_user(request):
    return bool(get_current_github_user(request).get("is_guest"))


def can_access_plan(request, plan):
    user = get_current_github_user(request)
    if not user:
        return False

    if user.get("is_guest"):
        return plan.guest_session_key == get_guest_key(request)
    return plan.github_login == user.get("login")


def login_required_redirect(view_func):
    def wrapper(request, *args, **kwargs):
        if not get_current_github_user(request):
            return redirect("/")
        return view_func(request, *args, **kwargs)

    return wrapper


def login_required_json(view_func):
    def wrapper(request, *args, **kwargs):
        if not get_current_github_user(request):
            return JsonResponse({"error": "로그인이 필요합니다."}, status=401)
        return view_func(request, *args, **kwargs)

    return wrapper


class MainView(View):
    def get(self, request):
        github_user = get_current_github_user(request)
        if github_user:
            return redirect("/dashboard/")
        return render(request, "base/index.html", {"user": None})


class DashboardView(View):
    @method_decorator(login_required_redirect)
    def get(self, request):
        github_user = get_current_github_user(request)
        plans = ProjectPlan.objects.filter(
            Q(github_login=github_user.get("login")) |
            Q(guest_session_key=get_guest_key(request))
        )
        return render(request, "dashboard/index.html", {
            "user": github_user,
            "plans": plans,
        })


class PlanFormPageView(View):
    @method_decorator(login_required_redirect)
    def get(self, request):
        github_user = get_current_github_user(request)
        return render(request, "plans/new.html", {"user": github_user})


@method_decorator(csrf_exempt, name="dispatch")
class PlanListView(View):
    @method_decorator(login_required_json)
    def get(self, request):
        github_user = get_current_github_user(request)
        plans = ProjectPlan.objects.filter(
            Q(github_login=github_user.get("login")) |
            Q(guest_session_key=get_guest_key(request))
        ).values("id", "title", "purposes", "date_start", "date_end", "created_at")
        return JsonResponse({"success": True, "plans": list(plans)})

    @method_decorator(login_required_json)
    def post(self, request):
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "잘못된 JSON 형식입니다."}, status=400)

        github_user = get_current_github_user(request)
        guest_key = get_guest_key(request)
        plan = ProjectPlan.objects.create(
            github_login=github_user.get("login", "guest"),
            guest_session_key=guest_key if github_user.get("is_guest") else None,
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


@method_decorator(csrf_exempt, name="dispatch")
class PlanDetailView(View):
    @method_decorator(login_required_json)
    def get(self, request, plan_id):
        plan = get_object_or_404(ProjectPlan, id=plan_id)
        if not can_access_plan(request, plan):
            return JsonResponse({"error": "권한이 없습니다."}, status=403)

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
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "잘못된 JSON 형식입니다."}, status=400)

        plan = get_object_or_404(ProjectPlan, id=plan_id)
        if not can_access_plan(request, plan):
            return JsonResponse({"error": "권한이 없습니다."}, status=403)

        plan.title = body.get("title", plan.title)
        plan.features = body.get("features", plan.features)

        modify_request = body.get("modify_request")
        if modify_request:
            prompt_data = body.copy()
            prompt_data["existing_plan"] = plan.ai_plan
            prompt = build_plan_prompt(prompt_data)
            new_ai_result = call_ai(prompt)
            plan.ai_plan = new_ai_result.get("text", plan.ai_plan)

        plan.save()
        return JsonResponse({"success": True, "ai_plan": plan.ai_plan})

    @method_decorator(login_required_json)
    def delete(self, request, plan_id):
        plan = get_object_or_404(ProjectPlan, id=plan_id)
        if not can_access_plan(request, plan):
            return JsonResponse({"error": "권한이 없습니다."}, status=403)

        plan.delete()
        return JsonResponse({"success": True, "message": "플랜이 삭제되었습니다."})


class PlanPageView(View):
    @method_decorator(login_required_redirect)
    def get(self, request, plan_id):
        plan = get_object_or_404(ProjectPlan, id=plan_id)
        if not can_access_plan(request, plan):
            return redirect("/dashboard/")

        return render(request, "plans/detail.html", {
            "user": get_current_github_user(request),
            "plan": plan,
            "summaries": plan.daily_summaries.all()[:7],
        })


@method_decorator(csrf_exempt, name="dispatch")
class SaveSummaryView(View):
    @method_decorator(login_required_json)
    def post(self, request, plan_id):
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "잘못된 JSON 형식입니다."}, status=400)

        plan = get_object_or_404(ProjectPlan, id=plan_id)
        if not can_access_plan(request, plan):
            return JsonResponse({"error": "권한이 없습니다."}, status=403)

        summary_data = body.get("summary", {})
        _, created = DailySummary.objects.update_or_create(
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


def edit_plan_view(request, plan_id):
    plan = get_object_or_404(ProjectPlan, id=plan_id)
    if not can_access_plan(request, plan):
        return redirect("/dashboard/")

    return render(request, "plans/new.html", {
        "user": get_current_github_user(request),
        "plan": plan,
        "is_edit_mode": True,
    })
