from fastapi import APIRouter, Depends
from schemas.auth import UserRegister, UserLogin, UserResponse, TokenResponse
from services.auth import AuthService
from utils.dependencies import get_current_user
from models.auth import User

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(data: UserRegister):
    return await AuthService.register(data)


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin):
    return await AuthService.login(data)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return User.from_dict(current_user)
