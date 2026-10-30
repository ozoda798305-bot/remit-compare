"""견적을 같은 기준(총 지불액 amount_krw)으로 맞추고, 검사하고, 순위·절약액·변화를 계산한다."""
from .promotions import fee_waiver_for
from .quote import Quote


def normalize(q: Quote, amount_krw: int) -> float:
    """총 amount_krw 원을 낼 때 받는 솜. 수수료 별도/포함 방식 차이를 없앤다."""
    return q.effective_rate * amount_krw


def check(q: Quote, mid: dict, prev_rate: float | None, rules: dict) -> list[str]:
    """실패·의심 기준. 빈 목록이면 통과."""
    problems = []
    if q.received_uzs <= 0 or q.total_paid_krw <= 0:
        return ["받는 금액 또는 지불액이 0"]
    gap = (q.effective_rate / mid["uzs_per_krw"] - 1) * 100
    if gap > rules["max_above_mid_pct"]:
        problems.append(f"시장 환율보다 {gap:.2f}% 높음(수집 오류 의심)")
    if gap < -rules["max_below_mid_pct"]:
        problems.append(f"시장 환율보다 {-gap:.2f}% 낮음(수집 오류 의심)")
    if prev_rate:
        change = (q.effective_rate / prev_rate - 1) * 100
        if abs(change) > rules["max_day_change_pct"]:
            problems.append(f"지난 실행 대비 {change:+.2f}% 변동")
    return problems


def build_table(quotes: list[Quote], mid: dict, cfg: dict, prev: dict, promos: list[dict] | None = None) -> dict:
    amount = cfg["amount_krw"]
    rows = []
    for q in quotes:
        key = f"{q.provider}|{q.method}"
        prev_rate = prev.get("rates", {}).get(key)
        problems = check(q, mid, prev_rate, cfg["check"])
        rows.append({
            **q.to_dict(),
            "key": key,
            "normalized_uzs": round(normalize(q, amount)),
            "hidden_cost_pct": round((1 - q.effective_rate / mid["uzs_per_krw"]) * 100, 2),
            "change_pct": round((q.effective_rate / prev_rate - 1) * 100, 2) if prev_rate else None,
            "problems": problems,
            "ok": not problems,
        })

    # 업체마다 가장 유리한 수취 방법 하나를 대표로 순위를 매긴다.
    # 순위는 같은 방식(카드 즉시 입금, 실시간 견적)끼리만. 은행 SWIFT 추정치는 참고선으로 따로 둔다.
    best_by_provider = {}
    for r in rows:
        if r["ok"] and (r["provider"] not in best_by_provider
                        or r["normalized_uzs"] > best_by_provider[r["provider"]]["normalized_uzs"]):
            best_by_provider[r["provider"]] = r
    ranking = sorted((r for r in best_by_provider.values() if r["kind"] == "live"), key=lambda r: -r["normalized_uzs"])
    for i, r in enumerate(ranking, 1):
        r["rank"] = i
    reference = [r for r in best_by_provider.values() if r["kind"] != "live"]
    live = ranking
    best = live[0] if live else None
    for r in reference:
        r["gap_vs_best_uzs"] = (best["normalized_uzs"] - r["normalized_uzs"]) if best else None

    # AI가 찾은 혜택 중 기존 고객도 받는 수수료 무료가 있으면 '혜택 반영' 금액을 계산한다
    for r in ranking:
        waiver = fee_waiver_for(r["provider"], promos or [])
        if waiver and r["fee_krw"]:
            r["promo_uzs"] = round(r["normalized_uzs"] + r["fee_krw"] * r["effective_rate"])
            r["promo_title"] = waiver["title"]

    # 지금 쓰는 업체 대비 절약액
    saving = None
    mine = best_by_provider.get(cfg_provider_name(cfg["my_provider"]))
    if best and mine and mine is not best:
        per_send = best["normalized_uzs"] - mine["normalized_uzs"]
        per_year = per_send * cfg["sends_per_month"] * 12
        saving = {"vs": mine["provider"], "per_send_uzs": per_send, "per_year_uzs": per_year,
                  "per_year_krw": round(per_year / mid["uzs_per_krw"])}

    worst_live = live[-1] if len(live) > 1 else None
    spread = (best["normalized_uzs"] - worst_live["normalized_uzs"]) if best and worst_live else 0

    return {
        "amount_krw": amount, "mid": mid, "rows": rows, "ranking": ranking, "reference": reference, "best": best,
        "saving": saving, "best_worst_gap_uzs": spread,
        "best_changed": bool(prev.get("best") and best and prev["best"] != best["provider"]),
        "prev_best": prev.get("best"), "prev_run_at": prev.get("run_at"),
    }


_NAMES = {"hanpass": "한패스", "e9pay": "E9pay", "gme": "GME", "gmoney": "G-Money", "hana": "하나은행"}


def cfg_provider_name(code: str) -> str:
    return _NAMES.get(code.lower(), code)
