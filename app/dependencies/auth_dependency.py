from fastapi import Depends, HTTPException, status

from app.models.user import User, UserRole
from app.services.auth_service import get_current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires admin privileges",
        )
    return current_user
