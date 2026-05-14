from pydantic import BaseModel, Field


class UserRegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    phone: str | None = Field(default=None, min_length=11, max_length=20)


class UserLoginRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class TokenResponse(BaseModel):
    token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    username: str
    phone: str | None = None
    created_at: str
