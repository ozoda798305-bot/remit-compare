"""업체 견적 한 건을 담는 자료형."""
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class Quote:
    provider: str            # 표시 이름 (예: 한패스)
    method: str              # 수취 방법 (예: UZCARD)
    send_krw: float          # 계산기에 넣은 금액
    fee_krw: float           # 송금 수수료
    total_paid_krw: float    # 보내는 사람이 실제로 내는 돈
    received_uzs: float      # 가족이 받는 솜
    source: str              # 수집 방식과 주소
    kind: str = "live"       # live(실시간 견적) / estimate(공식 기반 추정)
    note: str = ""
    collected_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    @property
    def effective_rate(self) -> float:
        """낸 돈 1원당 받는 솜."""
        return self.received_uzs / self.total_paid_krw

    def to_dict(self) -> dict:
        d = asdict(self)
        d["effective_rate"] = round(self.effective_rate, 6)
        return d


class ProviderError(Exception):
    pass
