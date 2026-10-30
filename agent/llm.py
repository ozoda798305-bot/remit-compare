"""Gemini 호출 도구. JSON 으로만 답하게 하고, 바쁘면(429·503) 쉬었다가 다음 모델로 넘어간다."""
import json
import os
import re
import time

import requests

MODELS = ("gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-3.7-flash")


def has_key() -> bool:
    return bool(os.getenv("GEMINI_API_KEY"))


def ask_json(prompt: str, temperature: float = 0.1) -> tuple[dict, str]:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY 없음")
    last = ""
    for model in MODELS:
        for attempt in range(2):  # 바쁘면 한 번만 더 해 보고 다음 모델로
            try:
                r = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    headers={"x-goog-api-key": key},
                    json={"contents": [{"parts": [{"text": prompt}]}],
                          "generationConfig": {"responseMimeType": "application/json", "temperature": temperature}},
                    timeout=45)
            except Exception as e:
                last = f"{model}: {type(e).__name__}"
                break
            if r.status_code == 200:
                text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                text = re.sub(r"^```(?:json)?|```$", "", text.strip()).strip()
                return json.loads(text), model
            last = f"{model}: HTTP {r.status_code}"
            if r.status_code in (429, 503):
                time.sleep(3)
                continue
            break
    raise RuntimeError(f"Gemini 호출 실패({last})")


def squash(text: str) -> str:
    """원문 대조용: 공백을 하나로 줄인다."""
    return re.sub(r"\s+", " ", text or "").strip()


def digits_in(number: float, text: str) -> bool:
    """숫자가 화면 글자 안에 실제로 있는지(쉼표·공백 구분 무시)."""
    target = str(int(round(number)))
    return target in re.sub(r"(?<=\d)[,\s.](?=\d{3})", "", text)
