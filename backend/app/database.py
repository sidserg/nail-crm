from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)

if settings.database_url.startswith("sqlite"):
    # SQLite's built-in lower() is ASCII-only; make it Unicode-aware (Cyrillic search)
    @event.listens_for(engine, "connect")
    def _sqlite_unicode_lower(dbapi_conn, _):
        dbapi_conn.create_function("lower", 1, lambda s: s.lower() if isinstance(s, str) else s)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
