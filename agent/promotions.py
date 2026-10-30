"""AI 단계 ①: 업체 공지·이벤트·텔레그램 채널 글을 읽어 '이번 주 혜택'을 뽑는다.

계산기 숫자에는 안 나오는 수수료 무료·우대 환율·쿠폰을 찾는다.
AI가 지어낸 혜택을 막기 위해, 근거 문장이 원문에 그대로 있는지 코드로 대조한다.
"""
import json
from datetime import date, datetime, timedelta
from pathlib import Path

from . import llm
from .browser import new_page

SOURCES = [
    {"provider": "한패스", "url": "https://www.hanpass.com/uz/event"},
    {"provider": "한패스", "url": "https://www.hanpass.com/uz/notice"},
    {"provider": "GME", "url": "https://www.gmeremit.com/board/notice"},
    {"provider": "G-Money", "url": "https://gmoneytrans.com/notice/"},
    {"provider": "E9pay", "url": "https://t.me/s/e9payuz"},
    {"provider": "E9pay", "url": "https://t.me/s/e9pay_uzbekistan"},
]
MAX_CHARS = 7000

PROMPT = """너는 한국에서 우즈베키스탄으로 돈을 보내는 근로자를 돕는 비서다. 오늘은 {today}이다.
아래는 송금 업체 '{provider}'의 공지·이벤트 페이지에서 가져온 글이다({url}).

한국→우즈베키스탄 송금에 쓸 수 있는 혜택만 골라라: 수수료 무료·할인, 우대 환율, 쿠폰, 캐시백, 추천인 보상, 송금 경품 이벤트.
개인정보 방침, 채용, 점검 안내, 다른 나라 전용 혜택, 이미 끝난 행사는 넣지 않는다. 없으면 빈 목록을 낸다.

JSON으로만 답한다:
{{"promotions": [{{
  "title": "혜택 이름(한국어)",
  "type": "fee_free | fee_discount | rate_bonus | coupon | cashback | event | other",
  "benefit": "무엇을 얼마나 주는지 한 문장(한국어)",
  "value_krw": 숫자 또는 null,
  "conditions": "조건 한 문장(한국어)",
  "new_customer_only": true | false | null,
  "uzbekistan": true | false | null,
  "valid_until": "YYYY-MM-DD" 또는 null,
  "evidence": "원문에서 글자 그대로 복사한 근거 문장(번역 금지, 80자 이내)"
}}]}}

[글]
{text}"""


def _page_text(ctx, url: str) -> str:
    page = new_page(ctx)
    try:
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        return page.evaluate("() => document.body ? document.body.innerText : ''")
    finally:
        page.close()


def _validate(p: dict, text: str, today: date) -> str | None:
    """문제가 있으면 이유를, 없으면 None."""
    ev = llm.squash(p.get("evidence", ""))
    if len(ev) < 6 or ev not in llm.squash(text):
        return "근거 문장이 원문에 없음(AI가 지어냈을 수 있음)"
    if p.get("valid_until"):
        try:
            if date.fromisoformat(p["valid_until"]) < today:
                return "이미 끝난 혜택"
        except ValueError:
            pass
    if p.get("uzbekistan") is False:
        return "우즈베키스탄 대상 아님"
    return None


def scan(ctx: dict, data_dir: Path, refresh_hours: int = 24, force: bool = False) -> dict:
    cache = data_dir / "promotions.json"
    prev = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
    if prev and not force:
        age = datetime.now() - datetime.fromisoformat(prev["scanned_at"])
        if age < timedelta(hours=refresh_hours):
            return {**prev, "from_cache": True}

    today = date.today()
    kept, rejected, errors, model = [], [], [], None
    old_keys = {(p["provider"], p["title"]) for p in prev.get("promotions", [])}
    for src in SOURCES:
        try:
            text = _page_text(ctx, src["url"])
            # 텔레그램 채널은 최신 글이 아래쪽에 있다
            text = text[-MAX_CHARS:] if "t.me/" in src["url"] else text[:MAX_CHARS]
            out, model = llm.ask_json(PROMPT.format(today=today.isoformat(), text=text, **src))
        except Exception as e:
            errors.append({**src, "error": f"{type(e).__name__}: {e}"[:200]})
            continue
        for p in out.get("promotions", []):
            p.update(provider=src["provider"], source_url=src["url"])
            reason = _validate(p, text, today)
            if reason:
                rejected.append({**p, "reason": reason})
            else:
                p["is_new"] = bool(prev) and (p["provider"], p["title"]) not in old_keys
                kept.append(p)

    result = {"scanned_at": datetime.now().isoformat(timespec="seconds"), "model": model,
              "promotions": kept, "rejected": rejected, "errors": errors,
              "sources": SOURCES, "from_cache": False}
    data_dir.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result


def fee_waiver_for(provider: str, promos: list[dict]) -> dict | None:
    """기존 고객 누구나 받는 수수료 무료 혜택이면 돌려준다(순위 옆 '혜택 반영' 계산용)."""
    for p in promos:
        if (p["provider"] == provider and p.get("type") == "fee_free"
                and p.get("new_customer_only") is False and p.get("uzbekistan") is not False):
            return p
    return None
