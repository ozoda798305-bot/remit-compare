"""송금 비교 에이전트 실행.

  python3 run.py                          # config.json 값으로 1회 실행
  python3 run.py --amount 1500000 --my-provider e9pay
  python3 run.py --providers hanpass,e9pay  # 브라우저 없이 빠르게

  python3 run.py --simulate-break gmoney  # 수집기 고장을 가정하고 AI 복구를 시험

단계: 1 입력 → 2 시장 환율 → 3 업체 견적 수집(실패 시 AI 복구) → 4 AI 혜택 읽기 → 5 검사·비교
      → 6 기록·변화 감지 → 7 보고서·메시지 → 8 알림
"""
import argparse
import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path

from agent import ai_recover, compare, history, llm, promotions, report
from agent.midrate import get_mid_rate
from agent.quote import ProviderError
from agent.notify import find_chat_id, send_telegram
from agent.providers import REGISTRY

ROOT = Path(__file__).parent
BROWSER_PROVIDERS = {"gme", "gmoney"}


def load_env():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "config.json"))
    ap.add_argument("--amount", type=int)
    ap.add_argument("--my-provider")
    ap.add_argument("--providers")
    ap.add_argument("--out", default=str(ROOT / "output"))
    ap.add_argument("--no-pdf", action="store_true")
    ap.add_argument("--no-ai", action="store_true", help="AI 단계(혜택 읽기·실패 복구)를 끈다")
    ap.add_argument("--refresh-promos", action="store_true", help="저장된 혜택을 무시하고 새로 읽는다")
    ap.add_argument("--simulate-break", default="", help="고장 난 것으로 가정할 수집기(쉼표 구분)")
    ap.add_argument("--site", help="웹 페이지로 낼 폴더(index.html·card.png·report.pdf를 복사)")
    ap.add_argument("--telegram-chat-id", action="store_true", help="봇에게 메시지를 보낸 사람의 채팅 ID를 출력하고 끝낸다")
    args = ap.parse_args()
    if args.telegram_chat_id:
        load_env()
        print(find_chat_id())
        return
    broken = {c.strip() for c in args.simulate_break.split(",") if c.strip()}
    load_env()

    log = []

    def step(name, status, detail=""):
        log.append({"step": name, "status": status, "detail": detail, "at": datetime.now().isoformat(timespec="seconds")})
        print(f"[{status}] {name} {detail}")

    # 1 입력
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    if args.amount:
        cfg["amount_krw"] = args.amount
    if args.my_provider:
        cfg["my_provider"] = args.my_provider
    if args.providers:
        cfg["providers"] = [p.strip() for p in args.providers.split(",")]
    amount = cfg["amount_krw"]
    run_at = datetime.now().isoformat(timespec="seconds")
    step("1 입력", "OK", f"{amount:,}원, 지금 쓰는 곳={cfg['my_provider']}, 업체={','.join(cfg['providers'])}")

    # 2 시장 환율
    mid = get_mid_rate()
    step("2 시장 환율", "OK", f"{mid['uzs_per_krw']:.4f} UZS/KRW ({mid['source']})")

    # 3 업체 견적 수집 (브라우저가 필요한 업체가 있을 때만 브라우저를 연다)
    quotes, failures = [], []
    need_browser = bool(BROWSER_PROVIDERS & set(cfg["providers"])) or not args.no_pdf
    ctx = {"config": cfg, "mid": mid}

    use_ai = not args.no_ai and llm.has_key()
    promo_result = {}

    def collect():
        for code in cfg["providers"]:
            t0 = time.time()
            try:
                if code in broken:
                    raise ProviderError("시험: 사이트 구조가 바뀌어 기존 수집기가 숫자를 못 찾았다고 가정")
                got = REGISTRY[code](amount, ctx)
                quotes.extend(got)
                step(f"3 견적·{code}", "OK", f"{len(got)}건 {time.time() - t0:.1f}s")
                continue
            except Exception as e:
                err = f"{type(e).__name__}: {e}"[:300]
                step(f"3 견적·{code}", "FAIL", str(e)[:200])
            # 실패하면 AI가 공개 페이지 화면 글자에서 견적을 다시 찾는다
            if use_ai and code in ai_recover.PAGES and "browser" in ctx:
                try:
                    q = ai_recover.recover(code, ctx)
                    quotes.append(q)
                    step(f"3 AI 복구·{code}", "OK", f"{q.send_krw:,.0f}원 → {q.received_uzs:,.0f}솜 ({q.source})")
                    continue
                except Exception as e2:
                    err += f" / {e2}"
                    step(f"3 AI 복구·{code}", "FAIL", str(e2)[:200])
            failures.append({"provider": compare.cfg_provider_name(code), "error": err[:400]})

    def read_promos():
        if not use_ai or "browser" not in ctx:
            step("4 AI 혜택 읽기", "SKIP", "GEMINI_API_KEY 없음 또는 --no-ai")
            return
        try:
            r = promotions.scan(ctx, ROOT / "data", cfg.get("promo_refresh_hours", 24), args.refresh_promos)
            promo_result.update(r)
            step("4 AI 혜택 읽기", "OK", f"혜택 {len(r['promotions'])}건, 걸러냄 {len(r['rejected'])}건"
                 f"{' (저장된 결과 사용)' if r.get('from_cache') else ''}")
        except Exception as e:
            step("4 AI 혜택 읽기", "FAIL", str(e)[:200])

    out_dir = Path(args.out) / run_at.replace(":", "").replace("-", "")[:15]
    out_dir.mkdir(parents=True, exist_ok=True)

    def finish(browser=None):
        if not quotes:
            step("5 검사·비교", "FAIL", "견적이 하나도 없음")
            return
        # 5 검사·비교
        hist_path = ROOT / "data" / "history.csv"
        prev = history.load_previous(hist_path)
        promos = promo_result.get("promotions", [])
        table = compare.build_table(quotes, mid, cfg, prev, promos)
        table["promotions"] = promo_result
        bad = [r for r in table["rows"] if not r["ok"]]
        step("5 검사·비교", "OK" if not bad else "WARN",
             f"통과 {len(table['rows']) - len(bad)}/{len(table['rows'])}, 1위={table['best']['provider'] if table['best'] else '-'}")
        # 6 기록·변화 감지
        history.append(hist_path, run_at, table)
        step("6 기록", "OK", f"1위 변경={table['best_changed']} (지난 1위 {prev.get('best')})")
        # 7 보고서·메시지
        msg_ko, msg_uz = report.message_ko(table, run_at), report.message_uz(table, run_at)
        (out_dir / "message_ko.txt").write_text(msg_ko, encoding="utf-8")
        (out_dir / "message_uz.txt").write_text(msg_uz, encoding="utf-8")
        html_path = out_dir / "report.html"
        html_path.write_text(report.render_html(table, run_at, history.series(hist_path), failures, msg_uz), encoding="utf-8")
        (out_dir / "quotes.json").write_text(json.dumps(
            {"run_at": run_at, "config": cfg, "table": table, "failures": failures}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        if browser and not args.no_pdf:
            report.write_pdf(html_path, out_dir / "report.pdf", browser)
            report.write_card(table, run_at, out_dir / "card.png", browser)
        step("7 보고서", "OK", str(out_dir))
        # 7-1 웹 페이지(GitHub Pages 등)로 낼 폴더
        if args.site:
            site = Path(args.site)
            site.mkdir(parents=True, exist_ok=True)
            shutil.copy(html_path, site / "index.html")
            for name in ("report.pdf", "card.png", "quotes.json"):
                if (out_dir / name).exists():
                    shutil.copy(out_dir / name, site / name)
            shutil.copy(hist_path, site / "history.csv")
            step("7-1 웹 페이지", "OK", str(site))
        # 8 알림
        link = os.getenv("SITE_URL") or cfg.get("site_url", "")
        step("8 알림", "OK", send_telegram(msg_uz, msg_ko, link, out_dir / "card.png"))
        print("\n" + msg_ko)

    if need_browser:
        from agent.browser import open_browser
        with open_browser() as b:
            ctx["browser"] = b
            collect()
            read_promos()
            finish(b)
    else:
        collect()
        read_promos()
        finish()

    (out_dir / "run_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
