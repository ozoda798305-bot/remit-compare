"""GME: 공개 홈페이지(gmeremit.com)의 실시간 환율 계산기를 브라우저로 열어 우즈베키스탄·UZS를 고르고 화면 숫자를 읽는다.

계산기가 내부적으로 부르는 /api/ 경로는 robots.txt 금지이므로 직접 부르지 않는다.
"""
import re

from ..browser import new_page, to_num
from ..quote import Quote, ProviderError

URL = "https://www.gmeremit.com/"

# 계산기 상자(보내는 금액~환율)를 찾아 돌려주는 스크립트
BOX_JS = """() => {
  const lab = [...document.querySelectorAll('label')].find(l => l.innerText.includes('받는 금액'));
  let box = lab; for (let i = 0; i < 6; i++) box = box.parentElement;
  return box;
}"""


def _box_state(page):
    return page.evaluate(f"""() => {{
      const box = ({BOX_JS})();
      return {{inputs: [...box.querySelectorAll('input')].map(i => i.value), text: box.innerText}};
    }}""")


def fetch(amount_krw: int, ctx: dict) -> list[Quote]:
    page = new_page(ctx)
    try:
        page.goto(URL, wait_until="networkidle")
        page.wait_for_selector("label:has-text('받는 금액')")
        # 보내는 금액 입력
        sender = page.evaluate_handle(f"() => ({BOX_JS})().querySelectorAll('input')[0]")
        sender.as_element().fill(str(amount_krw))
        # 받는 국가 목록 열기 → 우즈베키스탄 → UZS
        page.evaluate("""() => {
          const lab = [...document.querySelectorAll('label, p, span')].find(l => l.innerText.trim() === '받는 국가');
          let el = lab; for (let i = 0; i < 4 && el; i++) { const b = el.querySelector('button'); if (b) { b.click(); return; } el = el.parentElement; }
        }""")
        page.locator("button", has_text="우즈베키스탄").first.click()
        page.wait_for_timeout(1500)
        page.locator("button", has_text=re.compile(r"^\s*UZS\s*$")).first.click()
        page.wait_for_timeout(2500)
        st = _box_state(page)
        text = st["text"]
        if "UZS" not in text or len(st["inputs"]) < 2 or not st["inputs"][1]:
            raise ProviderError(f"GME 화면에서 UZS 견적을 읽지 못함: {text[:200]}")
        fee = to_num(re.search(r"수수료 포함\s*([\d,]+)\s*KRW", text).group(1))
        method = re.search(r"송금 방식\s*\n\s*(.+)", text).group(1).strip()
        sent = to_num(st["inputs"][0])
        return [Quote(
            provider="GME", method=method, send_krw=sent, fee_krw=fee,
            total_paid_krw=sent,  # 화면에 '수수료 포함'으로 표시: 보낸 금액 안에서 수수료를 뗀다
            received_uzs=to_num(st["inputs"][1]),
            source="브라우저 자동화, 공개 홈페이지 계산기 (gmeremit.com)",
        )]
    finally:
        page.close()
