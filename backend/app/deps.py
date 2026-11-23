from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import decode_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(401, "Требуется авторизация")
    user_id = decode_token(creds.credentials)
    if user_id is None:
        raise HTTPException(401, "Сессия истекла, войдите заново")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(401, "Пользователь не найден")
    return user
