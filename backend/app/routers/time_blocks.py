from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import TimeBlock
from ..schemas import TimeBlockCreate, TimeBlockOut
from ..slots import check_overlap

router = APIRouter(prefix="/api", tags=["time-blocks"], dependencies=[Depends(get_current_user)])


@router.post("/time-blocks", response_model=TimeBlockOut, status_code=201)
def create_time_block(body: TimeBlockCreate, db: Session = Depends(get_db)):
    check_overlap(db, body.start_at, body.end_at)
    block = TimeBlock(
        start_at=body.start_at,
        end_at=body.end_at,
        comment=body.comment,
    )
    db.add(block)
    db.commit()
    db.refresh(block)
    return block


@router.get("/time-blocks", response_model=list[TimeBlockOut])
def list_time_blocks(
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
    db: Session = Depends(get_db),
):
    start = datetime.combine(date_from, time.min)
    end = datetime.combine(date_to + timedelta(days=1), time.min)
    return (
        db.query(TimeBlock)
        .filter(TimeBlock.start_at < end, TimeBlock.end_at > start)
        .order_by(TimeBlock.start_at)
        .all()
    )


@router.delete("/time-blocks/{block_id}", status_code=204)
def delete_time_block(block_id: int, db: Session = Depends(get_db)):
    block = db.get(TimeBlock, block_id)
    if not block:
        raise HTTPException(404, "Блок не найден")
    db.delete(block)
    db.commit()
