"""결과물: 비교 보고서(HTML·PDF)와 메신저용 짧은 메시지(한국어·우즈벡어)."""
import html
from pathlib import Path


def won(x) -> str:
    return f"{x:,.0f}"


def som(x) -> str:
    return f"{x:,.0f}".replace(",", " ")


# ---------- 메시지 ----------

def _promos(t: dict) -> list[dict]:
    return (t.get("promotions") or {}).get("promotions", [])


def message_ko(t: dict, run_at: str) -> str:
    lines = [f"[송금 비교] {run_at[:16].replace('T', ' ')} · 총 {won(t['amount_krw'])}원 → 우즈베키스탄 카드"]
    for r in t["ranking"]:
        lines.append(f"{r['rank']}. {r['provider']} {som(r['normalized_uzs'])}솜")
    for r in t["reference"]:
        lines.append(f"참고) {r['provider']} {r['method']} 추정 {som(r['normalized_uzs'])}솜")
    if t["best"]:
        lines.append(f"→ 오늘 가장 유리: {t['best']['provider']}")
    if t["saving"]:
        s = t["saving"]
        lines.append(f"→ {s['vs']} 대신 쓰면 1회 {som(s['per_send_uzs'])}솜, 1년 약 {won(s['per_year_krw'])}원 이득")
    if t["best_changed"]:
        lines.append(f"⚠ 1위가 바뀜: {t['prev_best']} → {t['best']['provider']}")
    for p in _promos(t):
        until = f" (~{p['valid_until']})" if p.get("valid_until") else ""
        lines.append(f"🎁 {'[새 혜택] ' if p.get('is_new') else ''}{p['provider']}: {p['title']}{until}")
    return "\n".join(lines)


UZ_NAMES = {"한패스": "Hanpass", "하나은행": "Hana Bank"}


def uz(name: str) -> str:
    return UZ_NAMES.get(name, name)


def message_uz(t: dict, run_at: str) -> str:
    lines = [f"📊 Pul o'tkazmalari taqqoslovi · {run_at[:10]}",
             f"Jami {won(t['amount_krw'])} KRW → O'zbekiston kartasi"]
    for r in t["ranking"]:
        lines.append(f"{r['rank']}. {uz(r['provider'])} — {som(r['normalized_uzs'])} so'm")
    for r in t["reference"]:
        lines.append(f"Ma'lumot uchun: {uz(r['provider'])} SWIFT (taxminiy) — {som(r['normalized_uzs'])} so'm")
    if t["best"]:
        lines.append(f"✅ Bugun eng foydali: {uz(t['best']['provider'])}")
    if t["saving"]:
        s = t["saving"]
        lines.append(f"💰 {uz(s['vs'])} o'rniga: har safar +{som(s['per_send_uzs'])} so'm, yiliga ≈ {won(s['per_year_krw'])} KRW")
    if t["best_changed"]:
        lines.append(f"⚠️ Birinchi o'rin o'zgardi: {uz(t['prev_best'])} → {uz(t['best']['provider'])}")
    for p in _promos(t):
        # 원문(대개 우즈벡어) 근거 문장을 그대로 보여 준다
        lines.append(f"🎁 {'[Yangi] ' if p.get('is_new') else ''}{uz(p['provider'])}: {p['evidence'][:80]}")
    return "\n".join(lines)


# ---------- HTML ----------

CSS = """
:root{--ink:#14213d;--muted:#5c677d;--line:#e3e7ee;--bg:#f6f8fb;--accent:#0a7d5a;--accent-soft:#e3f4ee;--warn:#b5580e;--warn-soft:#fdf0e3;--bar:#9fb3c8}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:"Apple SD Gothic Neo","Noto Sans KR","Malgun Gothic",sans-serif;font-size:14px;line-height:1.5}
.page{max-width:900px;margin:0 auto;padding:32px 28px}
h1{font-size:24px;margin:0 0 4px}h2{font-size:16px;margin:28px 0 10px;padding-bottom:6px;border-bottom:2px solid var(--ink)}
.sub{color:var(--muted);margin:0}
.hero{display:grid;grid-template-columns:1.3fr 1fr 1fr;gap:12px;margin-top:20px}
.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px}
.card .k{font-size:12px;color:var(--muted)}.card .v{font-size:22px;font-weight:700;margin-top:4px}.card .d{font-size:12px;color:var(--muted);margin-top:4px}
.card.best{background:var(--accent-soft);border-color:#b7e2d3}.card.best .v{color:var(--accent)}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden}
th,td{padding:9px 10px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}
th{background:#eef2f7;font-size:12px;color:var(--muted);font-weight:600}
td.l,th.l{text-align:left}tr.top td{background:var(--accent-soft);font-weight:600}
.badge{display:inline-block;font-size:11px;padding:1px 7px;border-radius:999px;background:#eef2f7;color:var(--muted);margin-left:4px}
.badge.est{background:var(--warn-soft);color:var(--warn)}.badge.bad{background:#fde8e8;color:#b42318}
.bars .row{display:grid;grid-template-columns:110px 1fr 120px;gap:10px;align-items:center;margin:6px 0}
.bars .track{background:#eef2f7;border-radius:6px;height:18px;position:relative}.bars .fill{height:18px;border-radius:6px;background:var(--bar)}
.bars .row.top .fill{background:var(--accent)}.bars .num{text-align:right;font-variant-numeric:tabular-nums}
.uz{background:#fff;border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:8px;padding:14px 16px;white-space:pre-line}
.note{color:var(--muted);font-size:12px}.warn{background:var(--warn-soft);color:var(--warn);border-radius:8px;padding:10px 14px;margin-top:12px}
ul.src{padding-left:18px;margin:6px 0}ul.src li{margin:2px 0}
tr.ref td{color:var(--muted);background:#fafbfc;border-top:2px dashed var(--line)}
.badge.ai{background:#e8eefc;color:#2f5597}.badge.new{background:var(--accent-soft);color:var(--accent)}
.promo{background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:8px 0}
.promo .ev{font-size:12px;color:var(--muted);margin-top:4px;word-break:break-all}
svg,table,.uz,.hero,.bars,.promo{break-inside:avoid}
.links{margin:8px 0 0;font-size:13px}.links a{color:#2f5597}
.tw{overflow-x:auto;-webkit-overflow-scrolling:touch;border-radius:12px}
@media (max-width:640px){.page{padding:20px 16px}h1{font-size:20px}.hero{grid-template-columns:1fr}
 .bars .row{grid-template-columns:80px 1fr 96px}th,td{padding:7px 8px;font-size:13px}}
@media print{body{background:#fff}.page{padding:0}.links{display:none}}
"""


def _bars(t):
    if not t["ranking"]:
        return "<p class='note'>순위에 넣을 견적이 없습니다.</p>"
    vals = [r["normalized_uzs"] for r in t["ranking"]]
    lo, hi = min(vals) * 0.97, max(vals)
    out = []
    for r in t["ranking"]:
        w = 8 + 92 * (r["normalized_uzs"] - lo) / (hi - lo or 1)
        cls = "row top" if r["rank"] == 1 else "row"
        tag = " <span class='badge est'>추정</span>" if r["kind"] == "estimate" else ""
        out.append(f"<div class='{cls}'><div>{html.escape(r['provider'])}{tag}</div>"
                   f"<div class='track'><div class='fill' style='width:{w:.1f}%'></div></div>"
                   f"<div class='num'>{som(r['normalized_uzs'])}</div></div>")
    return "<div class='bars'>" + "".join(out) + "</div><p class='note'>막대 시작점은 0이 아니라 최저값의 97%입니다(차이를 보이게 하려고).</p>"


def _trend_svg(series: dict) -> str:
    pts = {k: v for k, v in series.items() if len(v) >= 2}
    if not pts:
        return "<p class='note'>실행 기록이 2회 이상 쌓이면 업체별 추이 그래프가 나옵니다.</p>"
    allv = [y for v in pts.values() for _, y in v]
    lo, hi = min(allv), max(allv)
    W, H, P = 820, 220, 40
    colors = ["#0a7d5a", "#2f5597", "#b5580e", "#7a3e9d", "#5c677d"]
    n = max(len(v) for v in pts.values())
    lines, legend = [], []
    for i, (name, v) in enumerate(pts.items()):
        c = colors[i % len(colors)]
        xy = [(P + (W - 2 * P) * j / max(n - 1, 1), H - P - (H - 2 * P) * (y - lo) / (hi - lo or 1)) for j, (_, y) in enumerate(v)]
        lines.append(f"<polyline fill='none' stroke='{c}' stroke-width='2' points='{' '.join(f'{x:.1f},{y:.1f}' for x, y in xy)}'/>")
        legend.append(f"<span style='color:{c}'>■</span> {html.escape(name)}")
    return (f"<svg viewBox='0 0 {W} {H}' width='100%' style='background:#fff;border:1px solid #e3e7ee;border-radius:12px'>"
            f"<text x='{P}' y='20' font-size='11' fill='#5c677d'>{som(hi)}솜</text>"
            f"<text x='{P}' y='{H - 10}' font-size='11' fill='#5c677d'>{som(lo)}솜</text>{''.join(lines)}</svg>"
            f"<p class='note'>{' &nbsp; '.join(legend)}</p>")


def render_html(t: dict, run_at: str, series: dict, failures: list, msg_uz: str) -> str:
    amt = t["amount_krw"]
    best, sv = t["best"], t["saving"]
    when = run_at[:16].replace("T", " ")
    hero = [f"<div class='card best'><div class='k'>오늘 가장 유리한 곳</div><div class='v'>{html.escape(best['provider']) if best else '-'}</div>"
            f"<div class='d'>가족이 받는 돈 {som(best['normalized_uzs']) if best else '-'}솜</div></div>"]
    if sv:
        hero.append(f"<div class='card'><div class='k'>{html.escape(sv['vs'])} 대신 쓰면</div><div class='v'>+{som(sv['per_send_uzs'])}솜</div>"
                    f"<div class='d'>1년이면 약 {won(sv['per_year_krw'])}원</div></div>")
    else:
        hero.append("<div class='card'><div class='k'>지금 쓰는 곳</div><div class='v'>이미 1위</div><div class='d'>바꿀 필요 없음</div></div>")
    hero.append(f"<div class='card'><div class='k'>1위와 꼴찌 차이 (실시간 견적)</div><div class='v'>{som(t['best_worst_gap_uzs'])}솜</div>"
                f"<div class='d'>시장 환율 {t['mid']['uzs_per_krw']:.4f}솜/원</div></div>")

    has_promo = any(r.get("promo_uzs") for r in t["ranking"])
    rank_rows = []
    for r in t["ranking"]:
        badge = "<span class='badge ai'>AI 복구</span>" if r.get("note") == "AI 복구" else ""
        ch = "-" if r["change_pct"] is None else f"{r['change_pct']:+.2f}%"
        promo = f"<td>{som(r['promo_uzs'])}</td>" if r.get("promo_uzs") else ("<td>-</td>" if has_promo else "")
        rank_rows.append(
            f"<tr class='{'top' if r['rank'] == 1 else ''}'><td>{r['rank']}</td><td class='l'>{html.escape(r['provider'])}{badge}</td>"
            f"<td class='l'>{html.escape(r['method'])}</td><td>{won(r['fee_krw'])}</td><td>{som(r['normalized_uzs'])}</td>"
            f"{promo}<td>{r['hidden_cost_pct']:.2f}%</td><td>{ch}</td></tr>")
    for r in t["reference"]:
        gap = f"1위보다 {som(r['gap_vs_best_uzs'])}솜 적음" if r.get("gap_vs_best_uzs") else ""
        rank_rows.append(
            f"<tr class='ref'><td>참고</td><td class='l'>{html.escape(r['provider'])}<span class='badge est'>추정</span></td>"
            f"<td class='l'>{html.escape(r['method'])}</td><td>{won(r['fee_krw'])}</td><td>{som(r['normalized_uzs'])}</td>"
            f"{'<td>-</td>' if has_promo else ''}<td>{r['hidden_cost_pct']:.2f}%</td><td>{gap}</td></tr>")

    all_rows = []
    for r in sorted(t["rows"], key=lambda r: -r["normalized_uzs"]):
        state = "통과" if r["ok"] else "<span class='badge bad'>" + html.escape("; ".join(r["problems"])) + "</span>"
        if r.get("note") == "AI 복구":
            state += " <span class='badge ai'>AI 복구</span>"
        all_rows.append(
            f"<tr><td class='l'>{html.escape(r['provider'])}</td><td class='l'>{html.escape(r['method'])}</td>"
            f"<td>{won(r['send_krw'])}</td><td>{won(r['fee_krw'])}</td><td>{won(r['total_paid_krw'])}</td>"
            f"<td>{som(r['received_uzs'])}</td><td>{r['effective_rate']:.4f}</td><td class='l'>{state}</td></tr>")

    fail_html = ""
    if failures:
        fail_html = "<div class='warn'><b>이번 실행에서 받지 못한 업체</b><br>" + "<br>".join(
            html.escape(f"{f['provider']}: {f['error']}") for f in failures) + "</div>"
    changed = ""
    if t["best_changed"]:
        changed = f"<div class='warn'>⚠ 지난 실행({t['prev_run_at'][:16]}) 대비 1위가 바뀌었습니다: {html.escape(t['prev_best'])} → {html.escape(best['provider'])}</div>"

    pr = t.get("promotions") or {}
    if pr:
        items = []
        for p in pr.get("promotions", []):
            new = "<span class='badge new'>새 혜택</span>" if p.get("is_new") else ""
            until = f" · ~{html.escape(p['valid_until'])}" if p.get("valid_until") else ""
            who = {True: "신규 고객만", False: "기존 고객도"}.get(p.get("new_customer_only"), "대상 확인 필요")
            items.append(
                f"<div class='promo'><div><b>{html.escape(p['provider'])}</b> · {html.escape(p['title'])}{new}"
                f"<span class='note'>{until} · {who}</span></div>"
                f"<div>{html.escape(p.get('benefit') or '')} {html.escape(p.get('conditions') or '')}</div>"
                f"<div class='ev'>원문: “{html.escape(p['evidence'])}” — <a href='{html.escape(p['source_url'])}'>{html.escape(p['source_url'])}</a></div></div>")
        rej = pr.get("rejected", [])
        rej_html = ("<p class='note'>AI가 찾았지만 뺀 것: " + "; ".join(
            html.escape(f"{x['provider']} {x['title']}({x['reason']})") for x in rej) + "</p>") if rej else ""
        promo_html = (f"<h2>이번 주 혜택 <span class='note'>(AI가 업체 공지·텔레그램 {len(pr.get('sources', []))}곳을 읽고 찾음, "
                      f"{html.escape(str(pr.get('scanned_at', ''))[:16])} · {html.escape(str(pr.get('model')))})</span></h2>"
                      + ("".join(items) or "<p class='note'>지금 쓸 수 있는 혜택이 없습니다.</p>") + rej_html
                      + "<p class='note'>근거 문장이 원문에 그대로 있는 혜택만 남깁니다. 끝난 혜택, 다른 나라 전용 혜택은 뺍니다.</p>")
    else:
        promo_html = ""

    sources = sorted({(r["provider"], r["source"]) for r in t["rows"]})
    src_html = "".join(f"<li><b>{html.escape(p)}</b>: {html.escape(s)}</li>" for p, s in sources)
    hana = next((r for r in t["rows"] if r["kind"] == "estimate"), None)

    page = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>송금 비교 보고서 {when}</title>
<meta property="og:title" content="한국 → 우즈베키스탄 송금 비교 {when[:10]}"><meta property="og:image" content="card.png"><style>{CSS}</style></head>
<body><div class="page">
<h1>한국 → 우즈베키스탄 송금 비교</h1>
<p class="sub">{when} 기준 · 총 {won(amt)}원을 낼 때 가족이 카드로 받는 금액(UZS) · 수수료 포함 기준으로 맞춤</p>
<p class="links"><a href="report.pdf">PDF 보고서</a> · <a href="card.png">요약 카드 이미지</a> · <a href="quotes.json">원본 데이터(JSON)</a></p>
<div class="hero">{''.join(hero)}</div>
{changed}{fail_html}
<h2>순위 (카드 즉시 입금 송금 앱, 업체별 가장 유리한 수취 방법)</h2>
<table><tr><th>순위</th><th class="l">업체</th><th class="l">수취 방법</th><th>수수료(원)</th><th>받는 금액(솜)</th>{'<th>혜택 반영</th>' if has_promo else ''}<th>숨은 비용</th><th>지난 실행 대비</th></tr>{''.join(rank_rows)}</table>
<p class="note">숨은 비용 = 시장 환율로 바꿨을 때보다 덜 받는 비율(수수료와 환율 마진 합계). 은행(SWIFT)은 송금 방식이 달라 순위에 넣지 않고 참고로만 보여 줍니다.</p>
{promo_html}
<h2>받는 금액 비교</h2>{_bars(t)}
<h2>최근 추이</h2>{_trend_svg(series)}
<h2>O'zbekcha qisqacha</h2><div class="uz">{html.escape(msg_uz)}</div>
<h2>수집한 견적 전체와 검사 결과</h2>
<table><tr><th class="l">업체</th><th class="l">수취 방법</th><th>입력 금액</th><th>수수료</th><th>총 지불액</th><th>받는 금액(솜)</th><th>솜/원</th><th class="l">검사</th></tr>{''.join(all_rows)}</table>
<h2>자료 출처와 방법</h2>
<ul class="src">{src_html}<li><b>시장 환율</b>: {html.escape(t['mid']['source'])} (갱신 {html.escape(str(t['mid']['updated']))})</li></ul>
{f"<p class='note'>하나은행은 앱 안에서만 견적이 나와 실시간 값이 아닙니다. {html.escape(hana['note'])}. 수수료·스프레드는 가정값이라 순위 참고용입니다.</p>" if hana else ""}
<p class="note">각 업체 앱의 최종 견적과 다를 수 있습니다. 송금 직전 앱에서 한 번 더 확인하세요.</p>
</div></body></html>"""
    # 휴대폰에서 넓은 표가 화면을 넘지 않게 표마다 가로 스크롤 틀을 씌운다
    return page.replace("<table>", "<div class='tw'><table>").replace("</table>", "</table></div>")


CARD_CSS = """
*{box-sizing:border-box;margin:0}body{width:1080px;height:1080px;background:#f6f8fb;font-family:"Apple SD Gothic Neo","Noto Sans KR","Noto Sans",sans-serif;color:#14213d}
.c{padding:64px 72px;height:100%;display:flex;flex-direction:column}
.t{font-size:44px;font-weight:800}.s{font-size:26px;color:#5c677d;margin-top:10px}
.best{margin-top:40px;background:#e3f4ee;border:2px solid #b7e2d3;border-radius:28px;padding:30px 36px}
.best .k{font-size:26px;color:#0a7d5a;font-weight:700}.best .v{font-size:64px;font-weight:800;color:#0a7d5a;margin-top:6px}
.best .d{font-size:28px;margin-top:6px}
.rows{margin-top:34px}.r{display:grid;grid-template-columns:60px 240px 1fr 260px;align-items:center;gap:16px;margin:14px 0;font-size:32px}
.r .n{color:#5c677d;font-weight:700}.r .tr{height:26px;background:#e3e7ee;border-radius:13px}.r .f{height:26px;border-radius:13px;background:#9fb3c8}
.r.top .f{background:#0a7d5a}.r .a{text-align:right;font-weight:700;font-variant-numeric:tabular-nums}
.foot{margin-top:auto;font-size:24px;color:#5c677d;line-height:1.5}.gift{font-size:26px;color:#14213d;margin-top:18px}
"""


def render_card(t: dict, run_at: str) -> str:
    """텔레그램에 붙일 1080×1080 요약 카드(우즈벡어). 숫자는 표와 같은 값을 그대로 쓴다."""
    rows = t["ranking"][:5]
    vals = [r["normalized_uzs"] for r in rows] or [1]
    lo, hi = min(vals) * 0.97, max(vals)
    items = "".join(
        f"<div class='r{' top' if r['rank'] == 1 else ''}'><div class='n'>{r['rank']}</div><div>{html.escape(uz(r['provider']))}</div>"
        f"<div class='tr'><div class='f' style='width:{8 + 92 * (r['normalized_uzs'] - lo) / (hi - lo or 1):.1f}%'></div></div>"
        f"<div class='a'>{som(r['normalized_uzs'])}</div></div>" for r in rows)
    best, sv = t["best"], t["saving"]
    save = f"{html.escape(uz(sv['vs']))} o'rniga +{som(sv['per_send_uzs'])} so'm" if sv else ""
    ref = "".join(f"Ma'lumot uchun: {html.escape(uz(r['provider']))} SWIFT (taxminiy) {som(r['normalized_uzs'])} so'm<br>" for r in t["reference"])
    promo = "".join(f"<div class='gift'>🎁 {html.escape(uz(p['provider']))}: {html.escape(p['evidence'][:64])}</div>" for p in _promos(t)[:1])
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{CARD_CSS}</style></head><body><div class="c">
<div class="t">Koreya → O'zbekiston pul o'tkazmalari</div>
<div class="s">{run_at[:16].replace('T', ' ')} · Jami {won(t['amount_krw'])} KRW → karta (so'm)</div>
<div class="best"><div class="k">Bugun eng foydali</div><div class="v">{html.escape(uz(best['provider'])) if best else '-'}</div>
<div class="d">{som(best['normalized_uzs']) if best else '-'} so'm · {save}</div></div>
<div class="rows">{items}</div>{promo}
<div class="foot">{ref}Kurslar har kuni avtomatik yangilanadi. Yuborishdan oldin ilovada tekshiring.</div>
</div></body></html>"""


def write_card(t: dict, run_at: str, png_path: Path, browser):
    page = browser.new_page(viewport={"width": 1080, "height": 1080})
    page.set_content(render_card(t, run_at), wait_until="load")
    page.screenshot(path=str(png_path))
    page.close()


def write_pdf(html_path: Path, pdf_path: Path, browser):
    page = browser.new_page()
    page.goto(html_path.resolve().as_uri())
    page.pdf(path=str(pdf_path), format="A4", print_background=True,
             margin={"top": "12mm", "bottom": "12mm", "left": "10mm", "right": "10mm"})
    page.close()
