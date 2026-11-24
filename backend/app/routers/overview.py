"""Read-only overview statistics.

Adds GET /api/overview/stats without touching existing endpoints or models.
"""
from calendar import monthrange
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Integer, cast, func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Appointment, BLOCKING_STATUSES

router = APIRouter(
    prefix="/api",
    tags=["overview"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/overview/stats", response_model=dict[str, int])
def overview_stats(
    year: int = Query(..., ge=1, le=9999),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    """Return active appointment counts per day of the requested month.

    Response keys are day numbers as strings ("1".."31"), values are counts of
    appointments with status confirmed/completed. Days without appointments are 0.
    """
    days_in_month = monthrange(year, month)[1]
    start = datetime(year, month, 1)
    end = datetime(year, month, days_in_month, 23, 59, 59, 999999)

    # GROUP BY the day-of-month of start_at. The range filter can use
    # ix_appointments_start; the day expression is dialect-specific because the
    # project supports both PostgreSQL (production) and SQLite (local demo).
    dialect_name = db.get_bind().dialect.name
    if dialect_name == "sqlite":
        day_expr = cast(func.strftime("%d", Appointment.start_at), Integer)
    else:
        day_expr = cast(func.extract("day", Appointment.start_at), Integer)

    rows = (
        db.query(day_expr.label("day"), func.count(Appointment.id).label("cnt"))
        .filter(
            Appointment.start_at >= start,
            Appointment.start_at <= end,
            Appointment.status.in_(BLOCKING_STATUSES),
        )
        .group_by(day_expr)
        .all()
    )

    stats: dict[str, int] = {str(day): 0 for day in range(1, days_in_month + 1)}

    for day_value, count in rows:
        stats[str(int(day_value))] = int(count)

    return stats
