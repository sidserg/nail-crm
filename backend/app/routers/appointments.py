from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import get_current_user
from ..models import Appointment, Client, Service, STATUSES
from ..schemas import (AppointmentCreate, AppointmentOut, AppointmentPatch,
                       SlotOut)
from ..slots import check_overlap, get_slots

router = APIRouter(prefix="/api", tags=["appointments"], dependencies=[Depends(get_current_user)])


def _load(db: Session, appt_id: int) -> Appointment:
    appt = (
        db.query(Appointment)
        .options(joinedload(Appointment.client), joinedload(Appointment.service))
        .filter(Appointment.id == appt_id)
        .first()
    )
    if appt is None:
        raise HTTPException(404, "Запись не найдена")
    return appt


@router.get("/appointments", response_model=list[AppointmentOut])
def list_appointments(
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
    db: Session = Depends(get_db),
):
    start = datetime.combine(date_from, time.min)
    end = datetime.combine(date_to + timedelta(days=1), time.min)
    return (
        db.query(Appointment)
        .options(joinedload(Appointment.client), joinedload(Appointment.service))
        .filter(Appointment.start_at < end, Appointment.end_at > start)
        .order_by(Appointment.start_at)
        .all()
    )


@router.post("/appointments", response_model=AppointmentOut, status_code=201)
def create_appointment(body: AppointmentCreate, db: Session = Depends(get_db)):
    client = db.get(Client, body.client_id)
    service = db.get(Service, body.service_id)
    if client is None:
        raise HTTPException(404, "Клиент не найден")
    if service is None:
        raise HTTPException(404, "Услуга не найдена")
    end = body.start_at + timedelta(minutes=service.duration_min)
    check_overlap(db, body.start_at, end)
    appt = Appointment(
        client_id=client.id,
        service_id=service.id,
        start_at=body.start_at,
        end_at=end,
        price=body.price if body.price is not None else service.price,
        comment=body.comment,
        source="owner",
    )
    db.add(appt)
    db.commit()
    return _load(db, appt.id)


@router.patch("/appointments/{appt_id}", response_model=AppointmentOut)
def update_appointment(appt_id: int, body: AppointmentPatch, db: Session = Depends(get_db)):
    appt = _load(db, appt_id)
    data = body.model_dump(exclude_unset=True)

    if "status" in data:
        if data["status"] not in STATUSES:
            raise HTTPException(422, "Недопустимый статус")
        appt.status = data["status"]
    if "client_id" in data:
        if db.get(Client, data["client_id"]) is None:
            raise HTTPException(404, "Клиент не найден")
        appt.client_id = data["client_id"]
    if "service_id" in data:
        service = db.get(Service, data["service_id"])
        if service is None:
            raise HTTPException(404, "Услуга не найдена")
        appt.service_id = service.id
    if "comment" in data:
        appt.comment = data["comment"] or ""
    if "price" in data:
        appt.price = data["price"] if data["price"] is not None else appt.service.price

    # Reschedule / service change -> recompute end time and re-check overlaps
    if "start_at" in data or "service_id" in data:
        service = db.get(Service, appt.service_id)
        start = data.get("start_at") or appt.start_at
        end = start + timedelta(minutes=service.duration_min)
        check_overlap(db, start, end, exclude_id=appt.id)
        appt.start_at, appt.end_at = start, end
        appt.reminder_24h_sent = False
        appt.reminder_2h_sent = False
        appt.client_confirmed = None

    db.commit()
    return _load(db, appt.id)


@router.delete("/appointments/{appt_id}")
def delete_appointment(appt_id: int, db: Session = Depends(get_db)):
    appt = db.get(Appointment, appt_id)
    if appt is None:
        raise HTTPException(404, "Запись не найдена")
    db.delete(appt)
    db.commit()
    return {"ok": True}


@router.get("/slots", response_model=list[SlotOut])
def free_slots(
    day: date = Query(alias="date"),
    service_id: int | None = None,
    db: Session = Depends(get_db),
):
    return get_slots(db, day, service_id, public=False)
