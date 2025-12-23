from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    gis_auth_username: str = Field(..., max_length=100, description="Your Sinarmas ArcGIS portal username")
    full_name: Optional[str] = None


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
