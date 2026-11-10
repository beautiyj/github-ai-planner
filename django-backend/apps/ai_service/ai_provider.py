import json
import os
import re
import time

import requests


def _call_gemini(prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        "models/gemini-2.5-flash:generateContent"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 8192,
            "responseMimeType": "application/json",
        },
    }

    last_error = None
    for attempt in range(3):
        try:
            response = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                params={"key": api_key},
                json=payload,
                timeout=30,
            )
            if response.status_code in {429, 500, 502, 503, 504}:
                last_error = RuntimeError(
                    f"Gemini API 오류: {response.status_code} - {response.text[:200]}"
                )
                if attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise last_error

            response.raise_for_status()
            data = response.json()
            candidates = data.get("candidates") or []
            if not candidates:
                raise ValueError(f"Gemini 응답에 candidates가 없습니다: {data}")

            content = candidates[0].get("content", {})
            parts = content.get("parts") or []
            if not parts:
                raise ValueError(f"Gemini 응답에 content.parts가 없습니다: {data}")
            return parts[0].get("text", "")
        except requests.RequestException as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
                continue
        except ValueError:
            raise

    if last_error:
        raise RuntimeError(f"Gemini 호출 실패: {last_error}")
    raise RuntimeError("Gemini 호출 실패: 알 수 없는 오류")


def call_ai(prompt: str) -> dict:
    text = _call_gemini(prompt)
    return {"text": text, "provider": "gemini"}


def parse_ai_json(raw: str) -> dict:
    if raw is None:
        raise ValueError("AI 응답이 비어 있습니다.")

    text = raw.strip()
    if not text:
        raise ValueError("AI 응답이 비어 있습니다.")

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    cleaned = text.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", cleaned, flags=re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise
