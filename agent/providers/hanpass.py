"""한패스: 홈페이지(hanpass.com) 환율 계산기가 부르는 견적 주소를 그대로 조회한다.

app.hanpass.com 에는 robots.txt 제한이 없다(www.hanpass.com 은 /api/ 만 금지).
"""
import requests

from ..quote import Quote, ProviderError

URL = "https://app.hanpass.com/app/v1/remittance/get-cost"
METHODS = ["UZCARD (Express)", "HUMO (Express)"]


def fetch(amount_krw: int, ctx: dict) -> list[Quote]:
    quotes = []
    for method in METHODS:
        body = {"inputAmount": str(amount_krw), "inputCurrencyCode": "KRW", "fromCurrencyCode": "KRW",
                "toCurrencyCode": "UZS", "toCountryCode": "UZ", "memberSeq": "1",
                "remittanceOption": method, "lang": "en"}
        d = requests.post(URL, json=body, timeout=20,
                          headers={"Accept-Language": "en", "User-Agent": "Mozilla/5.0"}).json()
        if d.get("resultCode") != "0":
            continue
        fee = float(d.get("transferFee", 0))
        quotes.append(Quote(
            provider="한패스", method=method.replace(" (Express)", ""),
            send_krw=float(d["fromAmount"]), fee_krw=fee,
            total_paid_krw=float(d.get("depositAmountIncludingFee", d["fromAmount"] + fee)),
            received_uzs=float(d["toAmount"]),
            source="웹 계산기 주소 조회 (app.hanpass.com)",
        ))
    if not quotes:
        raise ProviderError("한패스 견적 응답 없음")
    return quotes
