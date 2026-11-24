"""Salon settings (key-value) + free-slot calculation."""
from datetime import date, datetime, time, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .models import Appointment, BLOCKING_STATUSES, Service, Setting, TimeBlock

SETTINGS_DEFAULTS: dict[str, str] = {
    "salon_name": "Студия маникюра",
    "salon_address": "",
    "work_start": "09:00",
    "work_end": "21:00",
    "slot_step": "30",
    "work_days": "0,1,2,3,4,5,6",  # Mon=0 ... Sun=6
    "booking_horizon_days": "30",
    "min_lead_minutes": "60",  # minimal lead time for online booking
}


def get_settings(db: Session) -> dict:
    rows = db.query(Setting).all()
    data = dict(SETTINGS_DEFAULTS)
    data.update({r.key: r.value for r in rows})
    return data


def save_settings(db: Session, data: dict) -> dict:
    for key, value in data.items():
        if key not in SETTINGS_DEFAULTS:
            continue
        row = db.get(Setting, key)
        if row is None:
            db.add(Setting(key=key, value=str(value)))
        else:
            row.value = str(value)
    db.commit()
    return get_settings(db)


def hhmm_to_min(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def validate_settings(data: dict) -> None:
    ws = hhmm_to_min(data.get("work_start", "09:00"))
    we = hhmm_to_min(data.get("work_end", "21:00"))
    if ws >= we:
        raise HTTPException(422, "Начало рабочего дня должно быть раньше конца")
    step = int(data.get("slot_step", 30))
    if step not in (10, 15, 20, 30, 60):
        raise HTTPException(422, "Шаг сетки может быть 10/15/20/30/60 минут")
    days = data.get("work_days", "")
    if not days or any(d not in "0123456" for d in days.split(",")):
        raise HTTPException(422, "Некорректные рабочие дни")


def busy_intervals_combined(db: Session, day: date) -> list[tuple[datetime, datetime]]:
    """Все занятые интервалы дня: активные записи + блокировки мастера."""
    day_start = datetime.combine(day, time.min)
    day_end = day_start + timedelta(days=1)
    intervals: list[tuple[datetime, datetime]] = []
    intervals += (
        db.query(Appointment.start_at, Appointment.end_at)
        .filter(
            Appointment.status.in_(BLOCKING_STATUSES),
            Appointment.start_at < day_end,
            Appointment.end_at > day_start,
        )
        .all()
    )
    intervals += (
        db.query(TimeBlock.start_at, TimeBlock.end_at)
        .filter(TimeBlock.start_at < day_end, TimeBlock.end_at > day_start)
        .all()
    )
    return intervals


def check_overlap(db: Session, start: datetime, end: datetime, exclude_id: int | None = None) -> None:
    """Конфликт с записью или с блокировкой -> 409."""
    q = db.query(Appointment).filter(
        Appointment.status.in_(BLOCKING_STATUSES),
        Appointment.start_at < end,
        Appointment.end_at > start,
    )
    if exclude_id is not None:
        q = q.filter(Appointment.id != exclude_id)
    if q.first() is not None:
        raise HTTPException(409, "Это время уже занято другой записью")

    if (
        db.query(TimeBlock)
        .filter(TimeBlock.start_at < end, TimeBlock.end_at > start)
        .first()
        is not None
    ):
        raise HTTPException(409, "Это время заблокировано мастером")


def get_slots(db: Session, day: date, service_id: int | None, public: bool = False) -> list[dict]:
    st = get_settings(db)
    duration = int(st["slot_step"])
    if service_id is not None:
        service = db.get(Service, service_id)
        if service is None or (public and not service.is_active):
            raise HTTPException(404, "Услуга не найдена")
        duration = service.duration_min

    if str(day.weekday()) not in st["work_days"].split(","):
        return []

    start_min, end_min = hhmm_to_min(st["work_start"]), hhmm_to_min(st["work_end"])
    step = int(st["slot_step"])
    day_start = datetime.combine(day, time.min)
    busy = busy_intervals_combined(db, day)
    now = datetime.now()
    lead = timedelta(minutes=int(st["min_lead_minutes"]))

    slots = []
    m = start_min
    while m + duration <= end_min:
        s = day_start + timedelta(minutes=m)
        e = s + timedelta(minutes=duration)
        free = all(not (s < b_end and e > b_start) for b_start, b_end in busy)
        if public and s < now + lead:
            free = False
        slots.append({"start": s, "end": e, "available": free})
        m += step
    return slots
