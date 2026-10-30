"""브라우저 자동화(Playwright) 공용 도구. 사람이 공개 페이지를 여는 것과 같은 방식으로 화면 숫자를 읽는다."""
from contextlib import contextmanager


@contextmanager
def open_browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        try:  # 설치된 크롬이 있으면 그것을, 없으면 playwright 크로미움을 쓴다
            browser = p.chromium.launch(channel="chrome", headless=True)
        except Exception:
            browser = p.chromium.launch(headless=True)
        try:
            yield browser
        finally:
            browser.close()


def new_page(ctx: dict):
    page = ctx["browser"].new_page(locale="ko-KR", viewport={"width": 1280, "height": 900})
    page.set_default_timeout(30000)
    return page


def to_num(text: str) -> float:
    return float(text.replace(",", "").strip())
