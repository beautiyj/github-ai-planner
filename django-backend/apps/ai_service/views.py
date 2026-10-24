import json
from datetime import date
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404

from apps.common.auth import login_required_json, get_current_github_user, get_guest_key
from apps.plans.models import ProjectPlan, DailySummary
from apps.github_api.github_client import GitHubClient
from .ai_provider import call_ai, parse_ai_json
from .prompts import build_plan_prompt, build_summary_prompt


def can_access_plan(request, plan):
    user = get_current_github_user(request)
    if not user:
        return False
    if user.get("is_guest"):
        return plan.guest_session_key == get_guest_key(request)
    return plan.github_login == user.get("login")


def get_github_client(request):
    access_token = request.session.get("github_access_token")
    if not access_token:
        return None
    return GitHubClient(access_token)


@method_decorator(csrf_exempt, name="dispatch")
class GeneratePlanView(View):
    @method_decorator(login_required_json)
    def post(self, request):
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "잘못된 JSON 형식입니다."}, status=400)

        title = (body.get("title") or "").strip()
        purposes = body.get("purposes") or []
        features = (body.get("features") or "").strip()
        repo_url = (body.get("repo_url") or "").strip()

        if not title:
            return JsonResponse({"error": "프로젝트 제목을 입력해주세요."}, status=400)
        if not purposes:
            return JsonResponse({"error": "프로젝트 목적을 선택해주세요."}, status=400)
        if not features:
            return JsonResponse({"error": "구현 기능을 입력해주세요."}, status=400)

        repo_context = {}
        if repo_url:
            client = get_github_client(request)
            if client:
                try:
                    repo_name = repo_url.rstrip("/")
                    detail = client.get_repo_detail(repo_name)
                    readme = client.get_repo_readme(repo_name)
                    github_user = request.session.get("github_user", {})
                    recent_commits = client.get_recent_commits(repo_name, github_user.get("login"), per_page=5)
                    repo_context = {
                        "name": detail.get("name", repo_name.split("/")[-1]),
                        "description": detail.get("description", ""),
                        "language": detail.get("language", ""),
                        "readme": readme,
                        "recent_commits": recent_commits,
                    }
                except Exception:
                    repo_context = {}

        try:
            prompt_body = dict(body)
            if repo_context:
                prompt_body["repo_context"] = repo_context
            prompt = build_plan_prompt(prompt_body)
            result = call_ai(prompt)
            ai_plan = parse_ai_json(result["text"])
            return JsonResponse({
                "success": True,
                "ai_plan": ai_plan,
                "provider": result["provider"],
                "repo_context": repo_context,
            })
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=500)
        except json.JSONDecodeError:
            return JsonResponse({"error": "AI 응답 파싱 실패. 다시 시도해주세요."}, status=500)
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                return JsonResponse({
                    "error": "구글 AI 호출 한도가 초과되었습니다.",
                    "details": error_msg,
                }, status=429)
            if "404" in error_msg or "NOT_FOUND" in error_msg:
                return JsonResponse({
                    "error": "구글 AI 모델 주소 오류입니다.",
                    "details": error_msg,
                }, status=404)
            return JsonResponse({"error": f"플랜 생성 오류: {error_msg}"}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class DailySummaryView(View):
    @method_decorator(login_required_json)
    def post(self, request):
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "잘못된 JSON 형식입니다."}, status=400)

        plan_id = body.get("plan_id")
        if not plan_id:
            return JsonResponse({"error": "plan_id는 필수입니다."}, status=400)

        plan = get_object_or_404(ProjectPlan, id=plan_id)
        if not can_access_plan(request, plan):
            return JsonResponse({"error": "권한이 없습니다."}, status=403)

        try:
            prompt = build_summary_prompt(body)
            result = call_ai(prompt)
            summary = parse_ai_json(result["text"])

            target_date = body.get("date") or str(date.today())
            summary_payload = body.get("summary", {})
            DailySummary.objects.update_or_create(
                plan=plan,
                date=target_date,
                defaults={
                    "commits": body.get("commits", []),
                    "ai_summary": summary.get("summary", summary_payload.get("summary", "")),
                    "advice": summary.get("advice", summary_payload.get("advice", "")),
                    "mood": summary.get("mood", summary_payload.get("mood", "good")),
                    "progress_percent": summary.get("progress_percent", summary_payload.get("progress_percent", 0)),
                    "highlight": summary.get("highlight", summary_payload.get("highlight", "")) or "",
                },
            )

            return JsonResponse({
                "success": True,
                "summary": summary,
                "provider": result["provider"],
                "saved": True,
            })

        except Exception as e:
            return JsonResponse({"error": f"요약 생성 오류: {str(e)}"}, status=500)