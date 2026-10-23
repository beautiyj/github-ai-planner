import json
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from apps.common.auth import login_required_json
from .ai_provider import call_ai, parse_ai_json
from .prompts import build_plan_prompt, build_summary_prompt


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

        if not title:
            return JsonResponse({"error": "프로젝트 제목을 입력해주세요."}, status=400)
        if not purposes:
            return JsonResponse({"error": "프로젝트 목적을 선택해주세요."}, status=400)
        if not features:
            return JsonResponse({"error": "구현 기능을 입력해주세요."}, status=400)

        try:
            prompt = build_plan_prompt(body)
            result = call_ai(prompt)
            ai_plan = parse_ai_json(result["text"])
            return JsonResponse({
                "success": True,
                "ai_plan": ai_plan,
                "provider": result["provider"],
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

        try:
            prompt = build_summary_prompt(body)
            result = call_ai(prompt)
            summary = parse_ai_json(result["text"])
            return JsonResponse({
                "success": True,
                "summary": summary,
                "provider": result["provider"],
            })

        except Exception as e:
            return JsonResponse({"error": f"요약 생성 오류: {str(e)}"}, status=500)