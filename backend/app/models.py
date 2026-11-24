"""ORM models.

All datetimes are NAIVE and represent wall-clock time in the salon timezone
(config `TZ`, applied to every container). This keeps a single-master salon
app simple and free of timezone- conversion bugs.
"""
import uuid
from datetime import datetime

from sqlalchemy import (Boolean, Date, DateTime, Float, ForeignKey, Index,
                        Integer, String, Text, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

# Appointment statuses
CONFIRMED = "confirmed"    # Подтверждена
COMPLETED = "completed"    # Выполнена
CANCELLED = "cancelled"    # Отменена
NO_SHOW = "no_show"        # Неявка
STATUSES = (CONFIRMED, COMPLETED, CANCELLED, NO_SHOW)
BLOCKING_STATUSES = (CONFIRMED, COMPLETED)  # occupy a time slot


def gen_token() -> str:
    return uuid.uuid4().hex


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    login: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # normalized digits
    birth_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")  # allergies, design preferences...
    telegram_chat_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tg_token: Mapped[str] = mapped_column(String(32), unique=True, default=gen_token)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_clients_name", "name"),)


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False)  # minutes
    price: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    color: Mapped[str] = mapped_column(String(9), default="#d6336c")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # start + service duration
    status: Mapped[str] = mapped_column(String(16), default=CONFIRMED, nullable=False)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)  # snapshot, editable on completion
    comment: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(8), default="owner")  # owner | online
    client_confirmed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # via Telegram button
    reminder_24h_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    reminder_2h_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    client: Mapped[Client] = relationship(back_populates="appointments")
    service: Mapped[Service] = relationship()

    __table_args__ = (
        Index("ix_appointments_start", "start_at"),
        Index("ix_appointments_status", "status"),
        # PostgreSQL additionally gets an EXCLUDE constraint (see alembic migration)
        # that makes overlapping active appointments impossible at the DB level.
    )


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[Date] = mapped_column(Date, nullable=False)
    category: Mapped[str] = mapped_column(String(60), default="Материалы")
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Setting(Base):
    """Key-value store: work hours, slot step, salon name, etc."""
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), nullable=False)


class TimeBlock(Base):
    """Личные блокировки времени мастера (обед, больничный, личные дела)."""
    __tablename__ = "time_blocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    start_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    comment: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_time_blocks_start", "start_at"),
    )


