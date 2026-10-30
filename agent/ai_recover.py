"""AI 단계 ②: 수집기가 실패하면(사이트 구조 변경 등) 공개 페이지의 화면 글자 전체를 Gemini에게 주고 견적을 뽑게 한다.

AI가 낸 숫자는 화면 글자에 실제로 있어야 받아들이고, 이후 시장 환율 검사(compare.check)도 똑같이 통과해야 한다.
"""
from . import llm
from .browser import new_page
from .compare import cfg_provider_name
from .quote import Quote, ProviderError

PAGES = {
    "hanpass": "https://www.hanpass.com/uz",
    "e9pay": "https://www.e9pay.co.kr/",
    "gme": "https://www.gmeremit.com/",
    "gmoney": "https://gmoneytrans.com/send-money-from-korea-to-uzbekistan/",
}

PROMPT = """아래는 송금 업체 '{provider}' 공개 웹페이지의 화면 글자다(계산기 틀 안의 글자 포함).
한국 원화(KRW)를 보내 우즈베키스탄 솜(UZS)으로 받는 견적이 화면에 있으면 그 숫자를 뽑아라.
다른 나라·다른 통화(USD 등) 견적이면 found=false 로 답한다. 숫자를 계산하거나 추측하지 말고 화면에 있는 숫자만 쓴다.

JSON으로만 답한다:
{{"found": true|false, "sent_krw": 숫자, "fee_krw": 숫자, "fee_included": true|false,
  "received_uzs": 숫자, "method": "수취 방법", "evidence": "받는 금액이 적힌 부분을 화면에서 그대로 복사"}}

[화면 글자]
{text}"""


def _screen_text(ctx, url: str) -> str:
    page = new_page(ctx)
    try:
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(6000)
        parts = []
        for f in page.frames:
            try:
                parts.append(f.evaluate("""() => {
                  const vals = [...document.querySelectorAll('input')].map(i => i.value).filter(Boolean);
                  return (document.body ? document.body.innerText : '') + '\\n[입력칸 값] ' + vals.join(' | ');
                }"""))
            except Exception:
                pass
        return "\n".join(parts)[:12000]
    finally:
        page.close()


def recover(code: str, ctx: dict) -> Quote:
    if not llm.has_key():
        raise ProviderError("AI 복구 불가: GEMINI_API_KEY 없음")
    if "browser" not in ctx or code not in PAGES:
        raise ProviderError("AI 복구 불가: 대상 페이지 없음")
    name = cfg_provider_name(code)
    text = _screen_text(ctx, PAGES[code])
    out, model = llm.ask_json(PROMPT.format(provider=name, text=text))
    if not out.get("found"):
        raise ProviderError("AI 복구 실패: 화면에 우즈베키스탄 견적 없음")
    sent, fee, got = float(out["sent_krw"]), float(out.get("fee_krw") or 0), float(out["received_uzs"])
    if not (llm.digits_in(got, text) and llm.digits_in(sent, text)):
        raise ProviderError(f"AI 복구 거부: AI가 낸 숫자({sent:,.0f}→{got:,.0f})가 화면에 없음")
    return Quote(
        provider=name, method=out.get("method") or "card", send_krw=sent, fee_krw=fee,
        total_paid_krw=sent if out.get("fee_included") else sent + fee, received_uzs=got,
        source=f"AI 복구({model}, 공개 페이지 화면 글자에서 추출)", note="AI 복구",
    )
