"""E9pay: 홈페이지(e9pay.co.kr) 환전 시뮬레이션 계산기 주소를 조회한다.

송금 수수료는 홈페이지에 들어 있는 송금방법 목록(REMIT_FEE)에서 읽는다. robots.txt 없음.
"""
import json
import re

import requests

from ..quote import Quote, ProviderError

HOME = "https://www.e9pay.co.kr/"
CALC = "https://www.e9pay.co.kr/cmm/calcExchangeRate.do"
UA = {"User-Agent": "Mozilla/5.0"}


def _methods(html: str) -> list[dict]:
    m = re.search(r'"UZ_UZS":(\[.*?\])', html)
    if not m:
        raise ProviderError("E9pay 우즈베키스탄 송금방법 목록을 찾지 못함")
    return json.loads(m.group(1))


def fetch(amount_krw: int, ctx: dict) -> list[Quote]:
    s = requests.Session()
    s.headers.update(UA)
    methods = _methods(s.get(HOME, timeout=20).text)
    quotes = []
    for m in methods:
        form = {"DEFRAY_AMOUNT": amount_krw, "SEND_NATN_COD": "KR", "CRNCY_COD": "KRW",
                "RCVER_EXPECT_NATN_COD": m["REMIT_NATN_COD"], "RCVER_EXPECT_CRNCY_COD": "UZS",
                "SIMULATION_YN": "Y", "OVSE_FEE_PROMOTION_YN": "N", "TOGGLE": "", "LANG_COD": ""}
        r = s.post(CALC, data=form, timeout=20,
                   headers={"X-Requested-With": "XMLHttpRequest", "Referer": HOME}).json()
        if r.get("responseCode", "S") != "S" and "data" not in r:
            continue
        d = json.loads(r["data"])
        if d.get("RESULT_COD") != "S":
            continue
        fee = float(m.get("REMIT_FEE") or 0)
        quotes.append(Quote(
            provider="E9pay", method=m["IMT_EXCNG_IEM_NM"].strip(),
            send_krw=float(d["DEFRAY_AMOUNT"]), fee_krw=fee,
            total_paid_krw=float(d["DEFRAY_AMOUNT"]) + fee,
            received_uzs=float(d["RCVER_EXPECT_RECPT_AMOUNT"]),
            source="웹 계산기 주소 조회 (e9pay.co.kr)",
        ))
    if not quotes:
        raise ProviderError("E9pay 견적 응답 없음")
    return quotes
