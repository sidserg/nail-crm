from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Appointment, Service
from ..schemas import ServiceIn, ServiceOut

router = APIRouter(prefix="/api/services", tags=["services"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[ServiceOut])
def list_services(db: Session = Depends(get_db)):
    return db.query(Service).order_by(Service.is_active.desc(), Service.name).all()


@router.post("", response_model=ServiceOut)
def create_service(body: ServiceIn, db: Session = Depends(get_db)):
    service = Service(**body.model_dump())
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


@router.patch("/{service_id}", response_model=ServiceOut)
def update_service(service_id: int, body: ServiceIn, db: Session = Depends(get_db)):
    service = db.get(Service, service_id)
    if service is None:
        raise HTTPException(404, "Услуга не найдена")
    for k, v in body.model_dump().items():
        setattr(service, k, v)
    db.commit()
    db.refresh(service)
    return service


@router.delete("/{service_id}")
def delete_service(service_id: int, db: Session = Depends(get_db)):
    service = db.get(Service, service_id)
    if service is None:
        raise HTTPException(404, "Услуга не найдена")
    used = db.query(Appointment).filter(Appointment.service_id == service_id).count()
    if used:
        raise HTTPException(409, "По этой услуге есть записи — нельзя удалить. Отключите её (снимите «Активна»), чтобы скрыть из записи.")
    db.delete(service)
    db.commit()
    return {"ok": True}
