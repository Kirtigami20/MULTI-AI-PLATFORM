from fastapi import HTTPException, status
from bson import ObjectId
from database import get_collection
from models.auth import User
from schemas.auth import UserRegister, UserLogin, UserResponse, TokenResponse
from utils.security import hash_password, verify_password, create_access_token


class AuthService:

    @staticmethod
    async def register(data: UserRegister) -> UserResponse:
        users = get_collection("users")

        existing = await users.find_one({"email": data.email})
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        user = User(
            name=data.name,
            email=data.email,
            password=hash_password(data.password),
        )

        await users.insert_one(user.to_dict())

        return UserResponse(
            id=str(user._id),
            name=user.name,
            email=user.email,
            created_at=user.created_at,
        )

    @staticmethod
    async def login(data: UserLogin) -> TokenResponse:
        users = get_collection("users")

        user = await users.find_one({"email": data.email})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not verify_password(data.password, user["password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        token = create_access_token(str(user["_id"]))

        return TokenResponse(access_token=token)

    @staticmethod
    async def get_user_by_id(user_id: str) -> UserResponse:
        users = get_collection("users")

        user = await users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return User(
            name=user["name"],
            email=user["email"],
            password="",
        ).from_dict(user)
