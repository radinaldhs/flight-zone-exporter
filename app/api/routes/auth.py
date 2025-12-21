from fastapi import APIRouter, HTTPException, status, Depends
from app.models.user import UserCreate, UserLogin, UserResponse, User, Token
from app.services.user_service import UserService
from app.core.security import create_access_token
from app.core.dependencies import get_current_active_user
from app.models.user import UserInDB

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
async def register(user_create: UserCreate):
    """
    Register a new user with GIS credentials.

    - **username**: Username (3-50 characters)
    - **password**: User password (min 6 characters)
    - **full_name**: Optional full name
    - **gis_auth_username**: ArcGIS auth username
    - **gis_auth_password**: ArcGIS auth password
    - **gis_username**: GIS username
    - **gis_password**: GIS password
    """
    try:
        # Create user
        user = UserService.create_user(user_create)

        # Create access token
        access_token = create_access_token(data={"sub": user.id, "username": user.username})

        # Return user without sensitive data
        user_response = User(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at
        )

        return UserResponse(
            user=user_response,
            access_token=access_token,
            token_type="bearer"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=UserResponse, tags=["Authentication"])
async def login(user_login: UserLogin):
    """
    Login with username and password.

    Returns access token and user information.
    """
    user = UserService.authenticate_user(user_login.username, user_login.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token = create_access_token(data={"sub": user.id, "username": user.username})

    # Return user without sensitive data
    user_response = User(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at
    )

    return UserResponse(
        user=user_response,
        access_token=access_token,
        token_type="bearer"
    )


@router.get("/me", response_model=User, tags=["Authentication"])
async def get_current_user_info(current_user: UserInDB = Depends(get_current_active_user)):
    """
    Get current authenticated user information.
    """
    return User(
        id=current_user.id,
        username=current_user.username,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )
