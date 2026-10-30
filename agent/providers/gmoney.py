"""G-Money(지머니트랜스): 공개 페이지 '한국→우즈베키스탄 송금'을 브라우저로 열고, 페이지에 나오는 계산기 숫자를 읽는다.

계산기 틀(mapi.gmoneytrans.net)은 robots.txt 전체 금지이므로 그 주소를 직접 부르지 않는다.
"""
import re

from ..browser import new_page, to_num
from ..quote import Quote, ProviderError

URL = "https://gmoneytrans.com/send-money-from-korea-to-uzbekistan/"


def fetch(amount_krw: int, ctx: dict) -> list[Quote]:
    page = new_page(ctx)
    try:
        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_selector("iframe[src*='exratenew']")
        frame = None
        for _ in range(30):
            frame = next((f for f in page.frames if "exratenew" in f.url), None)
            if frame and "Receiving Amt" in (frame.evaluate("() => document.body ? document.body.innerText : ''") or ""):
                break
            page.wait_for_timeout(500)
        if frame is None:
            raise ProviderError("G-Money 계산기를 찾지 못함")

        def state():
            return frame.evaluate("""() => ({
              inputs: [...document.querySelectorAll('input')].filter(i => i.offsetParent !== null).map(i => i.value),
              text: document.body.innerText })""")

        def wait_numbers():
            for _ in range(30):  # 받는 금액은 계산 요청이 끝난 뒤에 채워진다
                st = state()
                nums = [v for v in st["inputs"] if re.fullmatch(r"[\d,]+", v or "")]
                if len(nums) >= 2:
                    break
                page.wait_for_timeout(500)
            return st, nums

        st, nums = wait_numbers()
        if nums and to_num(nums[0]) != amount_krw:
            visible = [i for i in frame.locator("input").all() if i.is_visible()]
            box = next(i for i in visible if re.fullmatch(r"[\d,]+", i.input_value() or ""))
            box.fill(str(amount_krw))
            box.press("Tab")
            page.wait_for_timeout(1500)
            st, nums = wait_numbers()
        text = st["text"]
        if len(nums) < 2:
            raise ProviderError(f"G-Money 화면 숫자 부족: {st['inputs']}")
        fee_m = re.search(r"Sending Fee\s*:\s*([\d,]+)", text)
        fee = to_num(fee_m.group(1)) if fee_m else 0.0
        method_m = re.search(r"Receiving Method\s*\n\s*(.+)", text)
        sent = to_num(nums[0])
        return [Quote(
            provider="G-Money", method=method_m.group(1).strip() if method_m else "card",
            send_krw=sent, fee_krw=fee, total_paid_krw=sent + fee,  # 수수료는 별도로 낸다
            received_uzs=to_num(nums[1]),
            source="브라우저 자동화, 공개 페이지 계산기 (gmoneytrans.com)",
        )]
    finally:
        page.close()
