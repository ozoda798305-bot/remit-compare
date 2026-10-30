"""텔레그램 알림(선택). TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID 가 있을 때만 보낸다.

요약 카드 이미지 + 우즈벡어 요약 + 웹 링크를 한 번에, 한국어 요약은 이어서 글로 보낸다.
"""
import os
from pathlib import Path

import requests


def send_telegram(msg_uz: str, msg_ko: str, link: str = "", card: Path | None = None) -> str:
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return "건너뜀(텔레그램 키 없음)"
    api = f"https://api.telegram.org/bot{token}"
    tail = f"\n\n🔗 {link}" if link else ""
    if card and card.exists():
        caption = msg_uz[:1000 - len(tail)] + tail  # 사진 설명은 1024자 제한
        with card.open("rb") as f:
            r = requests.post(f"{api}/sendPhoto", data={"chat_id": chat, "caption": caption},
                              files={"photo": f}, timeout=30)
    else:
        r = requests.post(f"{api}/sendMessage", json={"chat_id": chat, "text": msg_uz + tail}, timeout=15)
    if not r.ok:
        return f"실패 {r.status_code} {r.text[:120]}"
    r2 = requests.post(f"{api}/sendMessage", json={"chat_id": chat, "text": msg_ko + tail,
                                                   "disable_web_page_preview": True}, timeout=15)
    return "보냄" if r2.ok else f"사진은 보냄, 글 실패 {r2.status_code}"


def find_chat_id() -> str:
    """봇에게 아무 메시지나 보낸 뒤 실행하면 채팅 ID를 알려 준다."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        return "TELEGRAM_BOT_TOKEN 없음"
    d = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=15).json()
    chats = {u["message"]["chat"]["id"]: u["message"]["chat"].get("first_name") or u["message"]["chat"].get("title")
             for u in d.get("result", []) if "message" in u}
    return ", ".join(f"{cid} ({name})" for cid, name in chats.items()) or "메시지가 없음: 봇에게 먼저 아무 말이나 보낸다"
