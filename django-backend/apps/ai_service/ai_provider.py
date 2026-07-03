# import os
# import json
# import re
# import requests
#
# from google import genai
# from google.genai import types
#
#
# # AI Provider — Gemini API 연동
# # https://ai.google.dev/docs
# # 나중에 Claude/GPT 추가하려면 아래에 함수 추가하면 됨
#
# # ── Gemini API 호출 ───────────────────────────────────────────
#
# def _call_gemini(prompt: str) -> str:
#     api_key = os.getenv("GEMINI_API_KEY")
#     if not api_key:
#         raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")
#
#     # 1. 구글 공식 최신 클라이언트 초기화
#     client = genai.Client(api_key=api_key)
#
#     # 2. 무료 키(AQ...) 인증이 완벽하게 보장되는 공식 2.0 모델 지정
#     # 공식 라이브러리를 쓰면 주소(404)나 트래픽(429) 문제가 깔끔하게 해결됩니다.
#     response = client.models.generate_content(
#         model='gemini-2.0-flash',
#         contents=prompt,
#         config=types.GenerateContentConfig(
#             temperature=0.7,
#             max_output_tokens=2048,
#         )
#     )
#
#     return response.text
# # def _call_gemini(prompt: str) -> str:
# #     api_key = os.getenv("GEMINI_API_KEY")
# #     if not api_key:
# #         raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")
# #
# #     # # 404가 절대 안 나던 최초의 올바른 주소로 복구
# #     # url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
# #
# #         # 1. 429 해결: 무료 등급 키(AQ...)가 완벽하게 통과하는 1.5-flash 모델 사용
# #         # 2. 404 해결: v1beta 주소와 gemini-1.5-flash 명칭을 정확히 일치시킴
# #     url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
# #     payload = {
# #         "contents": [{"parts": [{"text": prompt}]}],
# #         "generationConfig": {
# #             "temperature": 0.7,
# #             "maxOutputTokens": 2048,
# #         },
# #     }
# #     response = requests.post(url, json=payload, timeout=30)
# #     response.raise_for_status()
# #
# #     data = response.json()
# #     return data["candidates"][0]["content"]["parts"][0]["text"]
#
#
# # # ── 메인 호출 함수 ────────────────────────────────────────────
# # def call_ai(prompt: str) -> dict:
# #     """
# #     AI API 호출 메인 함수
# #     현재: Gemini 무료 사용
# #     나중에 다른 AI 추가하려면 여기에 분기 추가
# #
# #     Returns: {"text": str, "provider": str}
# #     """
# #     text = _call_gemini(prompt)
# #     return {"text": text, "provider": "gemini"}
# def call_ai(prompt: str) -> dict:
#     """
#     AI API 호출 메인 함수
#     """
#     text = _call_gemini(prompt)
#     return {"text": text, "provider": "gemini"}
#
# def _call_gemini(prompt: str) -> str:
#     api_key = os.getenv("GEMINI_API_KEY")
#     if not api_key:
#         raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")
#
#     # 1. 구글 공식 최신 클라이언트 초기화
#     client = genai.Client(api_key=api_key)
#
#     # 2. 429 제한이 덜하고 안정적인 1.5-flash 모델 명시
#     # 공식 SDK를 거치면 v1/v1beta 주소 파싱 오류(404)를 완전히 방지합니다.
#     response = client.models.generate_content(
#         model='gemini-1.5-flash',  # 👈 2.0 대신 1.5로 지정
#         contents=prompt,
#         config=types.GenerateContentConfig(
#             temperature=0.7,
#             max_output_tokens=2048,
#         )
#     )
#
#     return response.text
#
# # ── JSON 파싱 헬퍼 ────────────────────────────────────────────
# def parse_ai_json(raw: str) -> dict:
#     """
#     AI 응답에서 JSON 추출
#     AI가 ```json ... ``` 블록으로 감싸는 경우 처리
#
#     예시:
# ```json
#     {"total_days": 30, ...}
# ```
#     → {"total_days": 30, ...} 로 변환
#     """
#     # ```json 또는 ``` 제거
#     cleaned = re.sub(r"```json\s*", "", raw, flags=re.IGNORECASE)
#     cleaned = re.sub(r"```\s*", "", cleaned)
#     cleaned = cleaned.strip()
#     return json.loads(cleaned)
import os
import json
import re
import requests


# ── Gemini API 호출 ───────────────────────────────────────────
def _call_gemini(prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")

    # 💡 AQ. 키든 AIzaSy 키든 구글 무료/종량제 키는 무조건 url 파라미터 인증을 씁니다.
    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        "models/gemini-2.5-flash:generateContent"
    )

    # 헤더에는 Content-Type만 넣고, 인증은 무조건 params로 처리합니다.
    headers = {"Content-Type": "application/json"}
    params = {"key": api_key}

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 8192,
            "responseMimeType": "application/json",  # JSON만 반환 강제
        },
    }

    # 401 에러를 완전히 차단하는 안전한 요청 방식
    response = requests.post(
        url,
        headers=headers,
        params=params,
        json=payload,
        timeout=30
    )
    response.raise_for_status()

    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


# ── 메인 호출 함수 ────────────────────────────────────────────
def call_ai(prompt: str) -> dict:
    """AI API 호출 메인 함수"""
    text = _call_gemini(prompt)
    return {"text": text, "provider": "gemini"}


# ── JSON 파싱 헬퍼 ────────────────────────────────────────────
def parse_ai_json(raw: str) -> dict:
    """AI 응답에서 JSON 추출"""
    cleaned = re.sub(r"```json\s*", "", raw, flags=re.IGNORECASE)
    cleaned = re.sub(r"```\s*", "", cleaned)
    cleaned = cleaned.strip()
    return json.loads(cleaned)