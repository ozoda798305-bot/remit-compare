"""실행 기록(data/history.csv). 지난 실행과 비교해 바뀐 것만 알리는 데 쓴다."""
import csv
from pathlib import Path

FIELDS = ["run_at", "provider", "method", "kind", "total_paid_krw", "received_uzs",
          "effective_rate", "normalized_uzs", "mid_uzs_per_krw", "ok", "rank"]


def load_previous(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return {}
    last = rows[-1]["run_at"]
    prev = [r for r in rows if r["run_at"] == last]
    rates = {f"{r['provider']}|{r['method']}": float(r["effective_rate"]) for r in prev}
    best = next((r["provider"] for r in prev if r["rank"] == "1" and r["kind"] == "live"), None)
    if best is None:
        live = sorted((r for r in prev if r["kind"] == "live" and r["ok"] == "True" and r["rank"]),
                      key=lambda r: int(r["rank"]))
        best = live[0]["provider"] if live else None
    return {"run_at": last, "rates": rates, "best": best}


def series(path: Path, days: int = 30) -> dict:
    """업체별 최근 실행들의 대표 수령액(차트용)."""
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["rank"] and r["kind"] == "live"]
    out = {}
    for r in rows:
        out.setdefault(r["provider"], []).append((r["run_at"], int(float(r["normalized_uzs"]))))
    return {k: v[-days:] for k, v in out.items()}


def append(path: Path, run_at: str, table: dict):
    new = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        for r in table["rows"]:
            w.writerow({"run_at": run_at, "provider": r["provider"], "method": r["method"], "kind": r["kind"],
                        "total_paid_krw": r["total_paid_krw"], "received_uzs": r["received_uzs"],
                        "effective_rate": r["effective_rate"], "normalized_uzs": r["normalized_uzs"],
                        "mid_uzs_per_krw": round(table["mid"]["uzs_per_krw"], 6), "ok": r["ok"],
                        "rank": r.get("rank", "")})
