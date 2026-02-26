from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime, timedelta
from app.core.security import decode_access_token
from app.services.user_service import UserService
from app.models.user import UserInDB, TokenData
from app.core.config import settings

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = UserService.get_user_by_id(user_id)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: UserInDB = Depends(get_current_user)
) -> UserInDB:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    return current_user


def get_current_active_subscriber(
    current_user: UserInDB = Depends(get_current_active_user)
) -> UserInDB:
    """
    Verify user has active subscription or is whitelisted
    Returns HTTP 402 Payment Required if subscription expired
    """
    if not current_user.is_subscription_active():
        # Check if in grace period
        if current_user.subscription_status == "grace_period":
            grace_end = current_user.subscription_end_date + timedelta(days=settings.SUBSCRIPTION_GRACE_PERIOD_DAYS)
            days_left = (grace_end - datetime.utcnow()).days

            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Your subscription expired. You have {days_left} days left in grace period. Please renew to continue."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Your subscription has expired. Please renew your subscription to access this service."
            )

    return current_user


def get_user_gis_credentials(current_user: UserInDB = Depends(get_current_active_subscriber)) -> dict:
    """Get user GIS credentials - requires active subscription"""
    credentials = UserService.get_user_gis_credentials(current_user.id)
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GIS credentials not found"
        )
    return credentials
