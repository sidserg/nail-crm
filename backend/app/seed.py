"""Idempotent seeding: owner account, default settings/services, optional demo data."""
import logging
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from .config import settings
from .models import (CANCELLED, COMPLETED, CONFIRMED, NO_SHOW, Appointment,
                     Client, Expense, Service, Setting, User)
from .security import hash_password
from .slots import SETTINGS_DEFAULTS

log = logging.getLogger("seed")

DEFAULT_SERVICES = [
    ("Маникюр (классический)", 60, 1500, "#d6336c"),
    ("Маникюр + гель-лак", 90, 2200, "#a61e4d"),
    ("Педикюр + гель-лак", 90, 2600, "#7048e8"),
    ("Наращивание ногтей", 150, 3500, "#1971c2"),
    ("Коррекция наращивания", 120, 2800, "#0ca678"),
    ("Дизайн / укрепление", 30, 400, "#f08c00"),
]


def seed(db: Session) -> None:
    # Owner
    if db.query(User).count() == 0:
        db.add(User(login=settings.owner_login, password_hash=hash_password(settings.owner_password)))
        log.info("Owner account created: %s", settings.owner_login)

    # Default settings
    for key, value in SETTINGS_DEFAULTS.items():
        if db.get(Setting, key) is None:
            db.add(Setting(key=key, value=value))

    # Default services
    if db.query(Service).count() == 0:
        for name, dur, price, color in DEFAULT_SERVICES:
            db.add(Service(name=name, duration_min=dur, price=price, color=color))
    db.commit()

    if settings.demo_seed and db.query(Client).count() == 0:
        _seed_demo(db)


def _seed_demo(db: Session) -> None:
    log.info("Seeding demo data…")
    svc = {s.name: s for s in db.query(Service).all()}
    today = date.today()

    def at(day_offset: int, hh: int, mm: int = 0) -> datetime:
        return datetime.combine(today + timedelta(days=day_offset), time(hh, mm))

    clients_data = [
        ("Анна Смирнова", "79161234567", "Аллергия на ацетон! Любит нюдовые оттенки, форма — мягкий квадрат.", date(1992, 4, 12)),
        ("Мария Иванова", "79265557788", "Красный гель-лак, миндаль. Постоянный клиент, приходит раз в 3 недели.", date(1988, 11, 3)),
        ("Екатерина Козлова", "79031112233", "Педикюр раз в месяц, предпочитает френч.", date(1995, 7, 21)),
        ("Ольга Петрова", "79150001122", "Наращивание, длина 2. Просит напоминания в Telegram.", date(1990, 2, 8)),
        ("Виктория Соколова", "79267778899", "", date(1998, 9, 30)),
        ("Дарья Волкова", "79998887766", "Не была давно — предложить акцию на обновление.", date(1993, 1, 17)),
        ("Алина Морозова", "79057776655", "Переехала? Уточнить при контакте.", date(1996, 5, 25)),
    ]
    clients = {}
    for name, phone, notes, bd in clients_data:
        c = Client(name=name, phone=phone, notes=notes, birth_date=bd)
        db.add(c)
        clients[name] = c
    db.flush()

    def appt(client: str, service: str, start: datetime, status: str, source: str = "owner", comment: str = ""):
        s = svc[service]
        db.add(Appointment(
            client_id=clients[client].id, service_id=s.id,
            start_at=start, end_at=start + timedelta(minutes=s.duration_min),
            status=status, price=s.price, source=source, comment=comment,
        ))

    # Today — a realistic workload
    appt("Анна Смирнова", "Маникюр + гель-лак", at(0, 10), COMPLETED)
    appt("Мария Иванова", "Маникюр (классический)", at(0, 12), COMPLETED)
    appt("Екатерина Козлова", "Педикюр + гель-лак", at(0, 14), CONFIRMED, "online", "Хочу френч, как в прошлый раз")
    appt("Ольга Петрова", "Наращивание ногтей", at(0, 16, 30), CONFIRMED)
    appt("Виктория Соколова", "Маникюр (классический)", at(0, 19, 30), CONFIRMED, "online")

    # Yesterday / recent past
    appt("Мария Иванова", "Маникюр + гель-лак", at(-1, 11), COMPLETED)
    appt("Анна Смирнова", "Дизайн / укрепление", at(-1, 13), COMPLETED)
    appt("Виктория Соколова", "Маникюр (классический)", at(-1, 15), NO_SHOW)
    appt("Екатерина Козлова", "Маникюр + гель-лак", at(-2, 10), COMPLETED)
    appt("Ольга Петрова", "Коррекция наращивания", at(-3, 12), COMPLETED)
    appt("Дарья Волкова", "Маникюр + гель-лак", at(-4, 16), CANCELLED)

    # History for analytics
    for off, (cl, se) in {
        -6: ("Анна Смирнова", "Маникюр + гель-лак"),
        -8: ("Мария Иванова", "Педикюр + гель-лак"),
        -10: ("Ольга Петрова", "Наращивание ногтей"),
        -13: ("Екатерина Козлова", "Маникюр + гель-лак"),
        -16: ("Виктория Соколова", "Маникюр (классический)"),
        -20: ("Анна Смирнова", "Маникюр + гель-лак"),
        -24: ("Мария Иванова", "Маникюр + гель-лак"),
        -27: ("Ольга Петрова", "Коррекция наращивания"),
    }.items():
        appt(cl, se, at(off, 12), COMPLETED)

    # Long-inactive clients (marketing list)
    appt("Дарья Волкова", "Маникюр + гель-лак", at(-75, 12), COMPLETED)
    appt("Алина Морозова", "Педикюр + гель-лак", at(-95, 14), COMPLETED)

    # Upcoming
    appt("Анна Смирнова", "Маникюр + гель-лак", at(1, 10), CONFIRMED)
    appt("Мария Иванова", "Маникюр (классический)", at(1, 12), CONFIRMED, "online")
    appt("Ольга Петрова", "Коррекция наращивания", at(3, 15), CONFIRMED)

    # Expenses
    db.add(Expense(date=today, category="Материалы", amount=1200, comment="Гель-лаки, базы, топы"))
    db.add(Expense(date=today - timedelta(days=2), category="Инструменты", amount=800, comment="Фрезы"))
    db.add(Expense(date=today - timedelta(days=10), category="Аренда", amount=15000, comment="Аренда места, ноябрь"))
    db.add(Expense(date=today - timedelta(days=5), category="Материалы", amount=2300, comment="Пилки, апельсиновые палочки"))
    db.commit()
    log.info("Demo data seeded")
