from datetime import datetime
from pydantic import BaseModel, EmailStr

from app.models.user import UserRole


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class AdminCreate(UserCreate):
    admin_secret: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
