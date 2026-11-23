"""Telegram bot process: long polling + reminder scheduler.

Run:  python -m app.bot
Requires TELEGRAM_BOT_TOKEN. If unset, the process stays idle (no crash loop).

Reminders: 24h and 2h before a confirmed appointment, with
[✅ Подтверждаю] [❌ Отменить] buttons. Cancellation frees the slot instantly.
"""
import asyncio
import logging
from datetime import datetime, timedelta

import httpx

from .config import settings
from .database import SessionLocal
from .models import Appointment, CANCELLED, CONFIRMED, Client
from .slots import get_settings
from .utils import format_phone

logging.basicConfig(level=logging.INFO, format="%(asctime)s bot %(levelname)s %(message)s")
log = logging.getLogger("bot")

POLL_TIMEOUT = 30
TICK_SECONDS = 60


def when_ru(dt: datetime) -> str:
    months = ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]
    return f"{dt.day} {months[dt.month - 1]} в {dt.strftime('%H:%M')}"


def keyboard(appt: Appointment, token: str) -> dict:
    return {"inline_keyboard": [[
        {"text": "✅ Подтверждаю", "callback_data": f"c:cfm:{appt.id}:{token}"},
        {"text": "❌ Отменить", "callback_data": f"c:ccl:{appt.id}:{token}"},
    ]]}


class Bot:
    def __init__(self, token: str):
        self.cli = httpx.AsyncClient(base_url=f"https://api.telegram.org/bot{token}/", timeout=POLL_TIMEOUT + 15)
        self.username: str | None = None

    async def api(self, method: str, **payload) -> dict | None:
        try:
            r = await self.cli.post(method, json=payload)
            data = r.json()
            if not data.get("ok"):
                log.warning("%s failed: %s", method, data)
                return None
            return data["result"]
        except httpx.HTTPError as e:
            log.warning("%s error: %s", method, e)
            return None

    # ---------------- updates ----------------
    async def handle_update(self, upd: dict) -> None:
        if "message" in upd:
            await self.handle_message(upd["message"])
        elif "callback_query" in upd:
            await self.handle_callback(upd["callback_query"])

    async def handle_message(self, msg: dict) -> None:
        chat_id = str(msg["chat"]["id"])
        text = msg.get("text", "")
        log.info("message from chat_id=%s: %s", chat_id, text[:60])
        if not text.startswith("/start"):
            await self.api("sendMessage", chat_id=chat_id,
                           text="Я бот-напоминатель студии маникюра 💅\nЧтобы получать напоминания о записи, откройте персональную ссылку, которую пришлёт мастер.")
            return
        payload = text.split(maxsplit=1)[1] if " " in text else ""
        if payload.startswith("c_"):
            token = payload[2:]
            db = SessionLocal()
            try:
                client = db.query(Client).filter(Client.tg_token == token).first()
                if client is None:
                    await self.api("sendMessage", chat_id=chat_id, text="Ссылка устарела — попросите мастера прислать новую 🙏")
                    return
                client.telegram_chat_id = chat_id
                db.commit()
                await self.api("sendMessage", chat_id=chat_id,
                               text=f"Здравствуйте, {client.name}! 🌸\nНапоминания подключены: я напишу за 24 часа и за 2 часа до визита. В сообщении будут кнопки «Подтверждаю» и «Отменить».")
            finally:
                db.close()
            return
        if settings.telegram_owner_chat_id and chat_id == settings.telegram_owner_chat_id:
            await self.api("sendMessage", chat_id=chat_id, text="Вы подключены как владелец ✅\nСюда будут приходить уведомления о новых онлайн-записях и отменах.")
        else:
            await self.api("sendMessage", chat_id=chat_id,
                           text="Здравствуйте! Я отправляю напоминания о записи 💅\nПопросите мастера прислать вам персональную ссылку для подключения.")

    async def handle_callback(self, cb: dict) -> None:
        data = cb.get("data", "")
        parts = data.split(":")
        if len(parts) != 4 or parts[0] != "c":
            await self.api("answerCallbackQuery", callback_query_id=cb["id"])
            return
        _, action, appt_id, token = parts
        chat_id = str(cb["message"]["chat"]["id"])
        original_text = cb["message"].get("text", "")

        db = SessionLocal()
        try:
            appt = db.get(Appointment, int(appt_id))
            if (appt is None or appt.client.tg_token != token
                    or appt.client.telegram_chat_id != chat_id):
                await self.api("answerCallbackQuery", callback_query_id=cb["id"], text="Кнопка недействительна")
                return
            if appt.status != CONFIRMED or appt.start_at < datetime.now():
                await self.api("answerCallbackQuery", callback_query_id=cb["id"], text="Запись уже неактуальна")
                await self.api("editMessageReplyMarkup", chat_id=chat_id, message_id=cb["message"]["message_id"], reply_markup={"inline_keyboard": []})
                return

            client_name = appt.client.name
            service_name = appt.service.name
            when = when_ru(appt.start_at)

            if action == "cfm":
                appt.client_confirmed = True
                db.commit()
                await self.api("answerCallbackQuery", callback_query_id=cb["id"], text="Спасибо! Ждём вас 🌸")
                await self.api("editMessageText", chat_id=chat_id, message_id=cb["message"]["message_id"],
                               text=original_text + "\n\n✅ <b>Вы подтвердили визит.</b> До встречи!", parse_mode="HTML")
                if settings.telegram_owner_chat_id:
                    await self.api("sendMessage", chat_id=settings.telegram_owner_chat_id,
                                   text=f"✅ {client_name} подтвердил(а) визит {when} ({service_name})")
            elif action == "ccl":
                appt.status = CANCELLED
                db.commit()
                await self.api("answerCallbackQuery", callback_query_id=cb["id"], text="Запись отменена")
                await self.api("editMessageText", chat_id=chat_id, message_id=cb["message"]["message_id"],
                               text=original_text + "\n\n❌ <b>Запись отменена.</b> Будем рады видеть вас в другой раз — свободные окошки всегда доступны по ссылке записи мастера.", parse_mode="HTML")
                if settings.telegram_owner_chat_id:
                    await self.api("sendMessage", chat_id=settings.telegram_owner_chat_id,
                                   text=f"❌ <b>Отмена через бота</b>\n{client_name} ({format_phone(appt.client.phone)}) отменил(а) запись {when} ({service_name}).\nСлот освобождён.", parse_mode="HTML")
        finally:
            db.close()

    # ---------------- reminders ----------------
    async def reminder_tick(self) -> None:
        db = SessionLocal()
        try:
            now = datetime.now()
            st = get_settings(db)
            place = st["salon_name"] + (f", {st['salon_address']}" if st["salon_address"] else "")
            appts = (
                db.query(Appointment)
                .filter(Appointment.status == CONFIRMED,
                        Appointment.start_at > now,
                        Appointment.start_at <= now + timedelta(hours=24))
                .all()
            )
            for a in appts:
                client = a.client
                if not client.telegram_chat_id:
                    continue
                delta = a.start_at - now
                if delta <= timedelta(hours=2):
                    if a.reminder_2h_sent:
                        continue
                    text = (f"⏰ <b>Скоро ждём вас!</b>\n{a.service.name} — сегодня в {a.start_at.strftime('%H:%M')}\n📍 {place}")
                    res = await self.api("sendMessage", chat_id=client.telegram_chat_id, text=text,
                                         parse_mode="HTML", reply_markup=keyboard(a, client.tg_token))
                    if res:
                        a.reminder_2h_sent = True
                        a.reminder_24h_sent = True
                else:
                    if a.reminder_24h_sent:
                        continue
                    text = (f"💅 <b>Напоминание о записи</b>\n{a.service.name}\n📅 {when_ru(a.start_at)}\n📍 {place}\n\n"
                            f"Пожалуйста, подтвердите визит или отмените его кнопкой ниже — так мастер сможет предложить освободившееся время другим клиентам.")
                    res = await self.api("sendMessage", chat_id=client.telegram_chat_id, text=text,
                                         parse_mode="HTML", reply_markup=keyboard(a, client.tg_token))
                    if res:
                        a.reminder_24h_sent = True
            db.commit()
        except Exception:
            log.exception("reminder tick failed")
            db.rollback()
        finally:
            db.close()

    async def reminder_loop(self) -> None:
        while True:
            await self.reminder_tick()
            await asyncio.sleep(TICK_SECONDS)

    # ---------------- main loop ----------------
    async def run(self) -> None:
        me = await self.api("getMe")
        if me:
            self.username = me.get("username")
            log.info("Bot @%s started", self.username)
        asyncio.create_task(self.reminder_loop())
        offset = None
        while True:
            result = await self.api("getUpdates", timeout=POLL_TIMEOUT, offset=offset,
                                    allowed_updates=["message", "callback_query"])
            if result is None:
                await asyncio.sleep(5)
                continue
            for upd in result:
                offset = upd["update_id"] + 1
                try:
                    await self.handle_update(upd)
                except Exception:
                    log.exception("update handling failed")


async def main() -> None:
    if not settings.telegram_bot_token:
        log.info("TELEGRAM_BOT_TOKEN is not set — bot is idle. Set it in .env to enable reminders.")
        await asyncio.Event().wait()
        return
    bot = Bot(settings.telegram_bot_token)
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
