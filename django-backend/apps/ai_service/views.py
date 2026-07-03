import json
from datetime import date
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .ai_provider import call_ai, parse_ai_json
from .prompts import build_plan_prompt, build_summary_prompt

# AI 관련 API 엔드포인트
# 플랜 생성 + 일일 요약 두 가지 기능

"""
브라우저 (HTML)           ai_service/views.py        AI (Gemini)
─────────────────────────────────────────────────────────────
폼 작성 후 버튼 클릭  →  GeneratePlanView.post()  →  프롬프트 전송
                      ←  ai_plan JSON 반환        ←  마일스톤 생성

오늘 커밋 불러오기    →  DailySummaryView.post()  →  프롬프트 전송
                      ←  summary JSON 반환        ←  요약 생성
                      
"""

# 나중에 리팩토링할 때 utils.py 로 분리하기 - 로그인함수들
# ── 로그인 확인 ───────────────────────────────────────────────
def login_required_json(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get("github_user"):
            return JsonResponse({"error": "로그인이 필요합니다."}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper

#
# # ── POST /ai/generate-plan/ ───────────────────────────────────
# @method_decorator(csrf_exempt, name="dispatch")
# class GeneratePlanView(View):
#     """
#     폼 데이터 받아서 Gemini AI에게 플랜 생성 요청
#     Request:  { title, purposes, skills, features, date_start, date_end }
#     Response: { ai_plan: { total_days, milestones, ... } }
#     """
#
#     @method_decorator(login_required_json)
#     def post(self, request):
#         # 1. 요청 바디 파싱
#         try:
#             body = json.loads(request.body)
#         except json.JSONDecodeError:
#             return JsonResponse({"error": "잘못된 JSON 형식입니다."}, status=400)
#
#         # 2. 필수값 검증(빈값으로 AI 호출하면 의미없는 결과 나오니까 전처리)
#         title    = body.get("title", "").strip()
#         purposes = body.get("purposes", [])
#         features = body.get("features", "").strip()
#
#         if not title:
#             return JsonResponse({"error": "프로젝트 제목을 입력해주세요."}, status=400)
#         if not purposes:
#             return JsonResponse({"error": "프로젝트 목적을 선택해주세요."}, status=400)
#         if not features:
#             return JsonResponse({"error": "구현 기능을 입력해주세요."}, status=400)
#
#         # 3. 프롬프트 생성 & AI 호출. rompts.py 의 함수 호출 & ai_provider.py 의 함수 호출
#         try:
#             prompt = build_plan_prompt(body)
#             result = call_ai(prompt)
#
#             # 4. AI 응답 JSON 파싱
#             ai_plan = parse_ai_json(result["text"])
#
#             return JsonResponse({
#                 "success": True,
#                 "ai_plan": ai_plan,
#                 "provider": result["provider"],
#             })
#
#         except ValueError as e:
#             # API 키 누락 등
#             return JsonResponse({"error": str(e)}, status=500)
#         except json.JSONDecodeError:
#             return JsonResponse(
#                 {"error": "AI 응답 파싱 실패. 다시 시도해주세요."}, status=500
#             )
#         except Exception as e:
#             return JsonResponse({"error": f"플랜 생성 오류: {str(e)}"}, status=500)
# ── POST /ai/generate-plan/ ───────────────────────────────────
@method_decorator(csrf_exempt, name="dispatch")
class GeneratePlanView(View):
    """
    폼 데이터 받아서 Gemini AI에게 플랜 생성 요청
    Request:  { title, purposes, skills, features, date_start, date_end }
    Response: { ai_plan: { total_days, milestones, ... } }
    """

    @method_decorator(login_required_json)
    def post(self, request):
        # 1. 요청 바디 파싱
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "잘못된 JSON 형식입니다."}, status=400)

        # 2. 필수값 검증(빈값으로 AI 호출하면 의미없는 결과 나오니까 전처리)
        title = body.get("title", "").strip()
        purposes = body.get("purposes", [])
        features = body.get("features", "").strip()

        if not title:
            return JsonResponse({"error": "프로젝트 제목을 입력해주세요."}, status=400)
        if not purposes:
            return JsonResponse({"error": "프로젝트 목적을 선택해주세요."}, status=400)
        if not features:
            return JsonResponse({"error": "구현 기능을 입력해주세요."}, status=400)

        # 3. 프롬프트 생성 & AI 호출
        try:
            prompt = build_plan_prompt(body)
            result = call_ai(prompt)

            # 4. AI 응답 JSON 파싱
            ai_plan = parse_ai_json(result["text"])

            return JsonResponse({
                "success": True,
                "ai_plan": ai_plan,
                "provider": result["provider"],
            })

        except ValueError as e:
            # API 키 누락 등
            return JsonResponse({"error": str(e)}, status=500)
        except json.JSONDecodeError:
            return JsonResponse(
                {"error": "AI 응답 파싱 실패. 다시 시도해주세요."}, status=500
            )
        except Exception as e:
            error_msg = str(e)

            # 💡 구글 API 오류 필터링링 (429 할당량 초과)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                return JsonResponse({
                    "error": "구글 API 호출 한도가 초과되었습니다(429). 무료 티어 사용 시 한국 IP 제한 때문일 수 있으니 요금제 카드 등록이나 VPN 우회를 확인해주세요.",
                    "details": error_msg
                }, status=429)

            # 💡 구글 API 오류 필터링 (404 주소/모델 오류)
            elif "404" in error_msg or "NOT_FOUND" in error_msg:
                return JsonResponse({
                    "error": "구글 AI 모델 주소 요청 오류(404)가 발생했습니다. ai_provider.py의 모델명 규격을 다시 확인해야 합니다.",
                    "details": error_msg
                }, status=404)  # 👈 500 에러 대신 리액트에 명확하게 404를 전달!

            # 그 외 기타 예측하지 못한 에러
            return JsonResponse({"error": f"플랜 생성 오류: {error_msg}"}, status=500)

"""
except ValueError as e:
    # API 키가 .env 에 없을 때
    # "GEMINI_API_KEY가 설정되지 않았습니다."

except json.JSONDecodeError:
    # AI가 JSON 형식이 아닌 텍스트 반환했을 때
    # 가끔 AI가 "죄송합니다..." 같은 텍스트 반환하는 경우

except Exception as e:
    # 네트워크 오류, 서버 오류 등 나머지 모든 오류

    ValueError    → API 키 설정 문제 → 개발자가 .env 확인해야 함
    JSONDecodeError → AI 응답 문제  → 다시 시도하면 될 수도 있음
    Exception     → 나머지 오류     → 서버 로그 확인 필요
"""


"""
views.py          → 요청 받고 반환 (창구)
    ↓ 호출
prompts.py        → 프롬프트 생성 (번역가)
    ↓ 전달
ai_provider.py    → AI API 호출 (실행자)
    ↓ 반환
views.py          → JSON 파싱 후 반환
"""
# ── POST /ai/daily-summary/ ───────────────────────────────────
@method_decorator(csrf_exempt, name="dispatch")
class DailySummaryView(View):
    """
    오늘 커밋 목록 받아서 AI가 진행 상황 요약
    Request:  { plan_id, date, commits, current_milestone, total_days, elapsed_days }
    Response: { summary: { summary, advice, mood, progress_percent, highlight } }
    """

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