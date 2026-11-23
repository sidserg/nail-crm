from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def strip_tz(v: datetime | None) -> datetime | None:
    """All times are salon wall-clock times; drop any tz info."""
    if v is not None and v.tzinfo is not None:
        v = v.replace(tzinfo=None)
    return v


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Auth ----------
class LoginIn(BaseModel):
    login: str
    password: str


class TokenOut(BaseModel):
    token: str
    login: str


class PasswordChangeIn(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=128)


# ---------- Clients ----------
class ClientIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=3, max_length=30)
    birth_date: date | None = None
    notes: str = ""


class ClientShort(ORMModel):
    id: int
    name: str
    phone: str


class ClientOut(ORMModel):
    id: int
    name: str
    phone: str
    birth_date: date | None
    notes: str
    telegram_chat_id: str | None
    tg_token: str
    created_at: datetime


class ClientStats(BaseModel):
    visits: int = 0
    total_spent: float = 0
    last_visit: datetime | None = None


# ---------- Services ----------
class ServiceIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    duration_min: int = Field(ge=5, le=600)
    price: float = Field(ge=0, le=1_000_000)
    color: str = "#d6336c"
    is_active: bool = True


class ServiceOut(ORMModel):
    id: int
    name: str
    duration_min: int
    price: float
    color: str
    is_active: bool


# ---------- Appointments ----------
class AppointmentCreate(BaseModel):
    client_id: int
    service_id: int
    start_at: datetime
    price: float | None = Field(default=None, ge=0, le=1_000_000)
    comment: str = ""

    _tz = field_validator("start_at")(strip_tz)


class AppointmentPatch(BaseModel):
    client_id: int | None = None
    service_id: int | None = None
    start_at: datetime | None = None
    status: str | None = None
    price: float | None = Field(default=None, ge=0, le=1_000_000)
    comment: str | None = None

    _tz = field_validator("start_at")(strip_tz)


class AppointmentOut(ORMModel):
    id: int
    client_id: int
    service_id: int
    start_at: datetime
    end_at: datetime
    status: str
    price: float | None
    comment: str
    source: str
    client_confirmed: bool | None
    created_at: datetime
    client: ClientShort
    service: ServiceOut


class ClientDetail(BaseModel):
    client: ClientOut
    stats: ClientStats
    appointments: list[AppointmentOut]


class SlotOut(BaseModel):
    start: datetime
    end: datetime
    available: bool


# ---------- Expenses ----------
class ExpenseIn(BaseModel):
    date: date
    category: str = Field(default="Материалы", max_length=60)
    amount: float = Field(gt=0, le=10_000_000)
    comment: str = ""


class ExpenseOut(ORMModel):
    id: int
    date: date
    category: str
    amount: float
    comment: str


# ---------- Public booking ----------
class BookIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=6, max_length=30)
    service_id: int
    start_at: datetime
    comment: str = Field(default="", max_length=500)

    _tz = field_validator("start_at")(strip_tz)
