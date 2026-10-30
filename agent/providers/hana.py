"""하나은행: 실시간 견적은 앱 안에만 있어 '은행 해외송금(USD, SWIFT) 경로 추정치'를 계산한다.

근거: 하나은행 해외송금 약관 제7조(입금액에서 송금수수료·전신료 차감), 제8조(전신환매도율 적용).
수수료·스프레드는 config.json 의 hana_estimate 가정값을 쓴다.
"""
from ..quote import Quote


def fetch(amount_krw: int, ctx: dict) -> list[Quote]:
    cfg = ctx["config"]["hana_estimate"]
    mid = ctx["mid"]
    krw_per_usd = 1 / mid["usd_per_krw"]
    uzs_per_usd = mid["uzs_per_krw"] * krw_per_usd

    fees = cfg["remit_fee_krw"] + cfg["cable_fee_krw"]
    tts = krw_per_usd * (1 + cfg["tts_spread_pct"] / 100)          # 전신환매도율 추정
    usd_sent = (amount_krw - fees) / tts
    usd_arrived = usd_sent - cfg["intermediary_fee_usd"]            # 중개은행 수수료
    uzs = usd_arrived * uzs_per_usd * (1 - cfg["uz_bank_spread_pct"] / 100)  # 현지 은행 환전
    return [Quote(
        provider="하나은행", method="USD 계좌송금(SWIFT)",
        send_krw=amount_krw, fee_krw=fees, total_paid_krw=amount_krw,
        received_uzs=round(uzs),
        source="약관 공식 + 시장 환율 + 가정 수수료(config.json)", kind="estimate",
        note=f"추정치: 전신환매도율≈{tts:,.2f}원, 중개 ${cfg['intermediary_fee_usd']}",
    )]
