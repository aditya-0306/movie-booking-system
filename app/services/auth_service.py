import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User, RefreshToken

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: int, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "role": role, "type": "access", "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _hash_token(raw_token: str) -> str:
    # Refresh tokens are stored hashed (like passwords) so a leaked database
    # dump doesn't hand out valid, usable refresh tokens directly.
    return hashlib.sha256(raw_token.encode()).hexdigest()


def create_refresh_token(db: Session, user_id: int) -> str:
    raw_token = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    db_token = RefreshToken(
        user_id=user_id,
        token_hash=_hash_token(raw_token),
        expires_at=expires_at,
    )
    db.add(db_token)
    db.commit()
    return raw_token


def rotate_refresh_token(db: Session, raw_token: str) -> tuple[str, str, User]:
    """
    Validates the given refresh token, revokes it, and issues a brand new
    access + refresh token pair. Rotation (instead of reusing the same
    refresh token indefinitely) means a stolen refresh token is only useful
    once before it's invalidated by the legitimate user's next request.
    """
    token_hash = _hash_token(raw_token)
    db_token = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == token_hash, RefreshToken.revoked.is_(False))
        .first()
    )

    if not db_token or db_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    db_token.revoked = True
    db.commit()

    user = db.query(User).filter(User.id == db_token.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    new_access = create_access_token(user.id, user.role.value)
    new_refresh = create_refresh_token(db, user.id)
    return new_access, new_refresh, user


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_access_token(token)
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
