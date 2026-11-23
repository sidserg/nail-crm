"""Telegram helpers shared by the API (notifications) and the bot process."""
import logging

import httpx

from .config import settings

log = logging.getLogger("notify")
_bot_username: str | None = None


def tg_api(method: str, payload: dict) -> dict | None:
    if not settings.telegram_bot_token:
        return None
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/{method}"
    try:
        r = httpx.post(url, json=payload, timeout=15)
        data = r.json()
        if not data.get("ok"):
            log.warning("Telegram %s failed: %s", method, data)
        return data
    except httpx.HTTPError as e:
        log.warning("Telegram %s error: %s", method, e)
        return None


def send_message(chat_id: str, text: str, reply_markup: dict | None = None) -> dict | None:
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return tg_api("sendMessage", payload)


def notify_owner(text: str) -> None:
    if settings.telegram_owner_chat_id:
        send_message(settings.telegram_owner_chat_id, text)


def get_bot_username() -> str | None:
    global _bot_username
    if _bot_username is None and settings.telegram_bot_token:
        data = tg_api("getMe", {})
        if data and data.get("ok"):
            _bot_username = data["result"]["username"]
    return _bot_username
