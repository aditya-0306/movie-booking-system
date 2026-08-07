from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.exception_handler import AppException
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.user_schema import (
    UserCreate, AdminCreate, UserLogin, UserOut, TokenPair, RefreshRequest, AccessTokenOut,
)
from app.services.auth_service import (
    hash_password, verify_password, create_access_token, create_refresh_token, rotate_refresh_token,
)
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    if repo.get_by_email(payload.email):
        raise AppException(400, "Email already registered")

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.CUSTOMER,
    )
    return repo.create(user)


@router.post("/register-admin", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_admin(payload: AdminCreate, db: Session = Depends(get_db)):
    """
    Admin accounts can't be self-served through normal signup -- that would let
    anyone grant themselves admin rights. Creating one requires knowing a
    server-side secret (set via ADMIN_BOOTSTRAP_SECRET), which only the
    deployer/operator has access to.
    """
    if payload.admin_secret != settings.ADMIN_BOOTSTRAP_SECRET:
        raise AppException(403, "Invalid admin bootstrap secret")

    repo = UserRepository(db)
    if repo.get_by_email(payload.email):
        raise AppException(400, "Email already registered")

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.ADMIN,
    )
    return repo.create(user)


@router.post("/login", response_model=TokenPair)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    user = repo.get_by_email(payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise AppException(401, "Incorrect email or password")

    access_token = create_access_token(user.id, user.role.value)
    refresh_token = create_refresh_token(db, user.id)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/token", response_model=AccessTokenOut, include_in_schema=False)
def login_for_swagger(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    This endpoint exists ONLY so Swagger UI's "Authorize" button has a real,
    spec-compliant OAuth2 token endpoint to call.

    Swagger's Authorize dialog always sends a form-encoded body with
    'username' + 'password' fields (per the OAuth2 password-flow spec) --
    never JSON, and never an 'email' field. That's a hard requirement of the
    OAuth2PasswordBearer scheme itself, not something we can change from the
    client side. So rather than bend the app's real /auth/login (JSON, used
    by actual API clients, Postman, and the test suite) to match Swagger's
    format, this endpoint adapts Swagger's form fields to our existing login
    logic instead. form_data.username is treated as the user's email.

    include_in_schema=False keeps it out of the visible endpoint list --
    it's plumbing for the "Authorize" button, not a real API operation.
    """
    repo = UserRepository(db)
    user = repo.get_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise AppException(401, "Incorrect email or password")

    access_token = create_access_token(user.id, user.role.value)
    return AccessTokenOut(access_token=access_token)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    new_access, new_refresh, _ = rotate_refresh_token(db, payload.refresh_token)
    return TokenPair(access_token=new_access, refresh_token=new_refresh)
