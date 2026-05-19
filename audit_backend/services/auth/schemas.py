from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class AdminUserResponse(BaseModel):
    id: str
    username: str
    display_name: str | None = None
    role: str


class TokenResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    admin_user: AdminUserResponse
