from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing token")
    user_id = decode_token(credentials.credentials, "access")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user disabled or not found")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if getattr(user, "role", None) != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin only")
    return user
