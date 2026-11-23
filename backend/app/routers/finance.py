from collections import defaultdict
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Appointment, COMPLETED, Client, Expense
from ..schemas import ExpenseIn, ExpenseOut

router = APIRouter(prefix="/api", tags=["finance"], dependencies=[Depends(get_current_user)])


# ---------------- Expenses ----------------
@router.get("/expenses", response_model=list[ExpenseOut])
def list_expenses(
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
    db: Session = Depends(get_db),
):
    return (
        db.query(Expense)
        .filter(Expense.date >= date_from, Expense.date <= date_to)
        .order_by(Expense.date.desc(), Expense.id.desc())
        .all()
    )


@router.post("/expenses", response_model=ExpenseOut, status_code=201)
def create_expense(body: ExpenseIn, db: Session = Depends(get_db)):
    expense = Expense(**body.model_dump())
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.delete("/expenses/{expense_id}")
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    expense = db.get(Expense, expense_id)
    if expense is None:
        raise HTTPException(404, "Расход не найден")
    db.delete(expense)
    db.commit()
    return {"ok": True}


# ---------------- Analytics ----------------
@router.get("/analytics/summary")
def analytics_summary(
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
    db: Session = Depends(get_db),
):
    """Revenue = sum of prices of COMPLETED appointments in the period."""
    start = datetime.combine(date_from, time.min)
    end = datetime.combine(date_to + timedelta(days=1), time.min)
    appts = (
        db.query(Appointment)
        .filter(Appointment.start_at >= start, Appointment.start_at < end)
        .all()
    )
    completed = [a for a in appts if a.status == COMPLETED]
    revenue = round(sum(a.price or 0 for a in completed), 2)

    by_day: dict[str, float] = defaultdict(float)
    svc_stats: dict[int, dict] = {}
    for a in completed:
        by_day[a.start_at.date().isoformat()] += a.price or 0
        s = svc_stats.setdefault(a.service_id, {"name": a.service.name, "count": 0, "revenue": 0.0})
        s["count"] += 1
        s["revenue"] += a.price or 0

    # fill missing days with zero for a nice chart
    days = []
    d = date_from
    while d <= date_to:
        days.append({"date": d.isoformat(), "revenue": round(by_day.get(d.isoformat(), 0.0), 2)})
        d += timedelta(days=1)

    expenses_total = round(
        sum(e.amount for e in db.query(Expense).filter(Expense.date >= date_from, Expense.date <= date_to).all()), 2
    )
    status_counts = {s: sum(1 for a in appts if a.status == s) for s in ("confirmed", "completed", "cancelled", "no_show")}
    top = sorted(svc_stats.values(), key=lambda x: (-x["count"], -x["revenue"]))[:5]
    for t in top:
        t["revenue"] = round(t["revenue"], 2)

    return {
        "revenue": revenue,
        "completed_count": len(completed),
        "avg_check": round(revenue / len(completed), 2) if completed else 0,
        "expenses": expenses_total,
        "net_profit": round(revenue - expenses_total, 2),
        "revenue_by_day": days,
        "top_services": top,
        "status_counts": status_counts,
    }


@router.get("/analytics/inactive")
def inactive_clients(days: int = Query(60, ge=7, le=365), db: Session = Depends(get_db)):
    """Clients whose last COMPLETED visit was more than `days` ago (marketing list)."""
    cutoff = datetime.now() - timedelta(days=days)
    result = []
    for client in db.query(Client).all():
        completed = [a for a in client.appointments if a.status == COMPLETED]
        if not completed:
            continue
        last = max(a.start_at for a in completed)
        if last < cutoff:
            result.append({
                "id": client.id,
                "name": client.name,
                "phone": client.phone,
                "last_visit": last.isoformat(timespec="minutes"),
                "days_ago": (datetime.now() - last).days,
                "visits": len(completed),
                "total_spent": round(sum(a.price or 0 for a in completed), 2),
                "has_telegram": bool(client.telegram_chat_id),
            })
    result.sort(key=lambda x: x["days_ago"], reverse=True)
    return result
