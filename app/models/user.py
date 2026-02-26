from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timedelta


class UserBase(BaseModel):
    gis_auth_username: str = Field(..., max_length=100, description="Your Sinarmas ArcGIS portal username")
    full_name: Optional[str] = None

    # Subscription fields
    is_whitelisted: bool = False
    subscription_status: str = "inactive"  # inactive|active|expired|grace_period
    subscription_end_date: Optional[datetime] = None
    plan_type: str = "monthly"  # monthly|free


class UserCreate(UserBase):
    gis_auth_password: str = Field(..., max_length=72, description="Your Sinarmas ArcGIS portal password")


class UserLogin(BaseModel):
    gis_auth_username: str
    gis_auth_password: str


class User(UserBase):
    id: str
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class UserInDB(User):
    hashed_gis_auth_password: str

    def is_subscription_active(self) -> bool:
        """Check if user has active subscription or is whitelisted"""
        if self.is_whitelisted:
            return True

        if self.subscription_status == "active":
            return True

        if self.subscription_status == "grace_period":
            # Check if grace period (3 days) hasn't expired
            if self.subscription_end_date:
                from app.core.config import settings
                grace_end = self.subscription_end_date + timedelta(days=settings.SUBSCRIPTION_GRACE_PERIOD_DAYS)
                return datetime.utcnow() < grace_end

        return False


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[str] = None


class UserResponse(BaseModel):
    user: User
    access_token: str
    token_type: str = "bearer"
    requires_payment: Optional[bool] = None
    payment_url: Optional[str] = None
    payment_id: Optional[str] = None
    amount: Optional[int] = None
    expires_at: Optional[datetime] = None
