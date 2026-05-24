from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_active_user
from app.core.security import create_access_token
from app.models.user import User, UserCreate, UserInDB, UserLogin, UserResponse
from app.services.arcgis_service import ArcGISService
from app.services.user_service import UserService

router = APIRouter()


def _public_user(user: UserInDB) -> User:
    return User(
        id=user.id,
        gis_auth_username=user.gis_auth_username,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication"],
)
async def register(user_create: UserCreate):
    """
    Register with your Sinarmas ArcGIS portal credentials.

    Credentials are validated against maps.sinarmasforestry.com before the account is
    created. The password is bcrypt-hashed for login and Fernet-encrypted so it can be
    replayed to the ArcGIS portal for step-1 token exchange.
    """
    if not ArcGISService.validate_gis_credentials(
        user_create.gis_auth_username, user_create.gis_auth_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid GIS Auth credentials (portal login).",
        )

    try:
        user = UserService.create_user(user_create)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    access_token = create_access_token(
        data={"sub": user.id, "gis_auth_username": user.gis_auth_username}
    )
    return UserResponse(user=_public_user(user), access_token=access_token, token_type="bearer")


@router.post("/login", response_model=UserResponse, tags=["Authentication"])
async def login(user_login: UserLogin):
    user = UserService.authenticate_user(user_login.gis_auth_username, user_login.gis_auth_password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect GIS Auth credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.id, "gis_auth_username": user.gis_auth_username}
    )
    return UserResponse(user=_public_user(user), access_token=access_token, token_type="bearer")


@router.get("/me", response_model=User, tags=["Authentication"])
async def get_current_user_info(current_user: UserInDB = Depends(get_current_active_user)):
    return _public_user(current_user)
