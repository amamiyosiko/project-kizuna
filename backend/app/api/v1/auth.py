from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.db.session import get_db
from app.models import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RefreshRequest, TokenResponse, UserProfile

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(user: User) -> TokenResponse:
    subject = str(user.id)
    return TokenResponse(
        access_token=create_access_token(subject),
        refresh_token=create_refresh_token(subject),
        must_change_password=bool(getattr(user, "must_change_password", False)),
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已停用")
    return _token_response(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    user_id = decode_token(payload.refresh_token, "refresh")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token invalid")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user disabled or not found")
    return _token_response(user)


@router.get("/me", response_model=UserProfile)
def me(user: User = Depends(get_current_user)):
    return UserProfile(
        id=user.id,
        username=user.username,
        role=getattr(user, "role", None) or "staff",
        status=user.status,
        must_change_password=bool(getattr(user, "must_change_password", False)),
    )


@router.post("/change-password", response_model=UserProfile)
def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="新密码至少需要 8 位")
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码不正确")
    user.password_hash = get_password_hash(payload.new_password)
    user.must_change_password = False
    db.add(user)
    db.commit()
    db.refresh(user)
    return me(user)
