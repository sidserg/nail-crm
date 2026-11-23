from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config import settings as app_settings
from ..database import get_db
from ..deps import get_current_user
from ..notify import get_bot_username
from ..slots import get_settings, save_settings, validate_settings

router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=[Depends(get_current_user)])


@router.get("")
def read_settings(db: Session = Depends(get_db)):
    data = get_settings(db)
    data["telegram_enabled"] = bool(app_settings.telegram_bot_token)
    data["bot_username"] = get_bot_username()
    data["tz"] = app_settings.tz
    return data


@router.put("")
def write_settings(body: dict, db: Session = Depends(get_db)):
    validate_settings({**get_settings(db), **body})
    return save_settings(db, body)
