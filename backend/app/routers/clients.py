from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import get_current_user
from ..models import Appointment, COMPLETED, Client
from ..schemas import (AppointmentOut, ClientDetail, ClientIn, ClientOut,
                       ClientStats)
from ..utils import normalize_phone

router = APIRouter(prefix="/api/clients", tags=["clients"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[ClientOut])
def list_clients(q: str = "", db: Session = Depends(get_db)):
    query = db.query(Client)
    if q.strip():
        pattern = f"%{q.strip().lower()}%"
        digits = normalize_phone(q)
        cond = func.lower(Client.name).like(pattern)
        if digits:
            cond = cond | Client.phone.like(f"%{digits}%")
        query = query.filter(cond)
    return query.order_by(Client.name).limit(200).all()


@router.post("", response_model=ClientOut)
def create_client(body: ClientIn, db: Session = Depends(get_db)):
    """Idempotent by phone: if the phone already exists, returns the existing client."""
    phone = normalize_phone(body.phone)
    if len(phone) < 6:
        raise HTTPException(422, "Укажите корректный номер телефона")
    existing = db.query(Client).filter(Client.phone == phone).first()
    if existing:
        return existing
    client = Client(name=body.name.strip(), phone=phone, birth_date=body.birth_date, notes=body.notes)
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@router.get("/{client_id}", response_model=ClientDetail)
def get_client(client_id: int, db: Session = Depends(get_db)):
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(404, "Клиент не найден")
    appts = (
        db.query(Appointment)
        .options(joinedload(Appointment.client), joinedload(Appointment.service))
        .filter(Appointment.client_id == client_id)
        .order_by(Appointment.start_at.desc())
        .limit(100)
        .all()
    )
    completed = [a for a in appts if a.status == COMPLETED]
    stats = ClientStats(
        visits=len(completed),
        total_spent=round(sum(a.price or 0 for a in completed), 2),
        last_visit=max((a.start_at for a in completed), default=None),
    )
    return ClientDetail(client=ClientOut.model_validate(client), stats=stats,
                        appointments=[AppointmentOut.model_validate(a) for a in appts])


@router.patch("/{client_id}", response_model=ClientOut)
def update_client(client_id: int, body: ClientIn, db: Session = Depends(get_db)):
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(404, "Клиент не найден")
    phone = normalize_phone(body.phone)
    if len(phone) < 6:
        raise HTTPException(422, "Укажите корректный номер телефона")
    clash = db.query(Client).filter(Client.phone == phone, Client.id != client_id).first()
    if clash:
        raise HTTPException(409, f"Этот номер уже записан у клиента «{clash.name}»")
    client.name = body.name.strip()
    client.phone = phone
    client.birth_date = body.birth_date
    client.notes = body.notes
    db.commit()
    db.refresh(client)
    return client


@router.delete("/{client_id}")
def delete_client(client_id: int, force: bool = Query(False), db: Session = Depends(get_db)):
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(404, "Клиент не найден")
    count = db.query(Appointment).filter(Appointment.client_id == client_id).count()
    if count and not force:
        raise HTTPException(409, f"У клиента есть записи ({count} шт.). Удалите их или подтвердите удаление вместе с записями.")
    db.delete(client)
    db.commit()
    return {"ok": True}
