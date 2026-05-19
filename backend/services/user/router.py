from fastapi import APIRouter, Depends

from backend.core.responses import Result
from backend.deps import require_user
from backend.services.user.schemas import UserLoginRequest, UserRegisterRequest, UserResponse
from backend.services.user.service import UserService, get_user_service

router = APIRouter(prefix="/api/v1/auth", tags=["user"])


@router.post("/register")
async def register(
    req: UserRegisterRequest,
    svc: UserService = Depends(get_user_service),
) -> Result[dict]:
    token, user = await svc.register(req.username, req.password, req.phone)
    return Result.ok({
        "token": token.model_dump(),
        "user": user.model_dump(),
    })


@router.post("/login")
async def login(
    req: UserLoginRequest,
    svc: UserService = Depends(get_user_service),
) -> Result[dict]:
    token, user = await svc.login(req.username, req.password)
    return Result.ok({
        "token": token.model_dump(),
        "user": user.model_dump(),
    })


@router.get("/me")
async def get_me(
    user_id: str = Depends(require_user),
    svc: UserService = Depends(get_user_service),
) -> Result[UserResponse]:
    user = await svc.get_me(user_id)
    return Result.ok(user)
