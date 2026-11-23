"""Public online booking — no auth. Rate-limited per IP."""
import time as pytime
from collections import defaultdict, deque
from datetime import date, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from ..config import settings as app_settings
from ..database import get_db
from ..models import Appointment, Client, Service
from ..notify import get_bot_username, notify_owner
from ..schemas import BookIn, ServiceOut, SlotOut
from ..slots import check_overlap, get_settings, get_slots
from ..utils import format_phone, normalize_phone

router = APIRouter(prefix="/api/public", tags=["public"])

_book_hits: dict[str, deque] = defaultdict(deque)
RATE_LIMIT = 5          # bookings
RATE_WINDOW = 3600      # per hour, per IP


def _rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "?"
    now = pytime.monotonic()
    hits = _book_hits[ip]
    while hits and now - hits[0] > RATE_WINDOW:
        hits.popleft()
    if len(hits) >= RATE_LIMIT:
        raise HTTPException(429, "Слишком много заявок. Попробуйте позже или позвоните мастеру.")
    hits.append(now)


@router.get("/config")
def public_config(db: Session = Depends(get_db)):
    st = get_settings(db)
    return {
        "salon_name": st["salon_name"],
        "salon_address": st["salon_address"],
        "work_days": st["work_days"],
        "booking_horizon_days": int(st["booking_horizon_days"]),
        "tz": app_settings.tz,
        "bot_username": get_bot_username(),
        "demo": app_settings.demo_seed,
    }


@router.get("/services", response_model=list[ServiceOut])
def public_services(db: Session = Depends(get_db)):
    return db.query(Service).filter(Service.is_active.is_(True)).order_by(Service.name).all()


@router.get("/slots", response_model=list[SlotOut])
def public_slots(
    day: date = Query(alias="date"),
    service_id: int = Query(),
    db: Session = Depends(get_db),
):
    st = get_settings(db)
    horizon = int(st["booking_horizon_days"])
    if day < date.today() or day > date.today() + timedelta(days=horizon):
        return []
    return [s for s in get_slots(db, day, service_id, public=True) if s["available"]]


@router.post("/book", status_code=201)
def book(body: BookIn, request: Request, background: BackgroundTasks, db: Session = Depends(get_db)):
    _rate_limit(request)
    phone = normalize_phone(body.phone)
    if len(phone) < 10:
        raise HTTPException(422, "Укажите корректный номер телефона (10–11 цифр)")
    service = db.get(Service, body.service_id)
    if service is None or not service.is_active:
        raise HTTPException(404, "Услуга недоступна для записи")

    st = get_settings(db)
    horizon = int(st["booking_horizon_days"])
    day = body.start_at.date()
    if day < date.today() or day > date.today() + timedelta(days=horizon):
        raise HTTPException(422, "Эта дата недоступна для онлайн-записи")
    if body.start_at < datetime.now() + timedelta(minutes=int(st["min_lead_minutes"])):
        raise HTTPException(422, "Слишком близко к текущему времени — выберите другой слот")

    # The chosen start must be a valid free slot for this service
    slots = get_slots(db, day, service.id, public=True)
    match = next((s for s in slots if s["start"] == body.start_at and s["available"]), None)
    if match is None:
        raise HTTPException(409, "Этот слот уже занят или недоступен. Выберите другое время.")

    end = body.start_at + timedelta(minutes=service.duration_min)
    check_overlap(db, body.start_at, end)  # double safety

    client = db.query(Client).filter(Client.phone == phone).first()
    if client is None:
        client = Client(name=body.name.strip(), phone=phone)
        db.add(client)
        db.flush()

    appt = Appointment(
        client_id=client.id, service_id=service.id,
        start_at=body.start_at, end_at=end,
        price=service.price, comment=body.comment, source="online",
    )
    db.add(appt)
    db.commit()

    when = body.start_at.strftime("%d.%m %H:%M")
    background.add_task(
        notify_owner,
        f"🆕 <b>Новая онлайн-запись</b>\n{client.name} ({format_phone(phone)})\n"
        f"{service.name} — {when}\n{('Комментарий: ' + body.comment) if body.comment else ''}",
    )
    return {
        "ok": True,
        "appointment": {
            "start_at": appt.start_at.isoformat(timespec="minutes"),
            "end_at": appt.end_at.isoformat(timespec="minutes"),
            "service": service.name,
            "price": service.price,
        },
        "salon_name": st["salon_name"],
        "salon_address": st["salon_address"],
    }
