"""
FleetGuard authentication: SSO-only (no password login — unlike Meridian,
there's no non-SSO fallback here since every demo user signs in via
Microsoft). Issues our own short-lived JWT after verifying a Microsoft
token, then every protected route depends on get_current_user or
require_admin below.

Role model: User.role is "admin" | "fleet_owner". Admins see every
fleet; fleet_owner users are scoped to their own fleet_owner_id via
get_fleet_scope (returns None for admin = "no filter", or an int to
filter Vehicle.fleet_owner_id by).
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt as jose_jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12  # 12 hours — a demo/work-day session, not a week

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def hash_password(password: str) -> str:
    # bcrypt directly (not passlib's CryptContext) — passlib's bcrypt
    # backend-version-detection code breaks against newer bcrypt package
    # releases (AttributeError: module 'bcrypt' has no attribute '__about__'),
    # a known passlib/bcrypt incompatibility. Calling bcrypt directly sidesteps it.
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jose_jwt.encode({"sub": str(user_id), "exp": expire}, settings.jwt_secret_key, algorithm=ALGORITHM)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise credentials_exception
    try:
        payload = jose_jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise credentials_exception
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise credentials_exception
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return current_user


def get_fleet_scope(current_user: User = Depends(get_current_user)) -> Optional[int]:
    """Returns None for admin (no filter — sees everything), or the
    caller's fleet_owner_id to filter Vehicle queries by."""
    if current_user.role == "admin":
        return None
    return current_user.fleet_owner_id
