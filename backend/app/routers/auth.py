from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import LoginIn, PasswordChangeIn, TokenOut
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.login == body.login.strip()).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Неверный логин или пароль")
    return TokenOut(token=create_access_token(user.id), login=user.login)


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "login": user.login}


@router.post("/change-password")
def change_password(
    body: PasswordChangeIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(400, "Текущий пароль указан неверно")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"ok": True}
