from pydantic import BaseModel, Field


class CreateAdminRequest(BaseModel):
    username: str
    password: str
    display_name: str | None = None
    role: str = "auditor"


class UpdateAdminRequest(BaseModel):
    username: str | None = None
    password: str | None = None
    display_name: str | None = None
    role: str | None = None
    is_active: bool | None = None


class AdminUserResponse(BaseModel):
    id: str
    username: str
    display_name: str | None = None
    role: str
    is_active: bool
    last_login_at: str | None = None
    created_at: str | None = None


class AdminListResponse(BaseModel):
    items: list[AdminUserResponse]


class RetentionPolicyResponse(BaseModel):
    id: str
    name: str
    hot_days: int
    warm_days: int
    cold_days: int
    is_active: bool


class UpdateRetentionPolicyRequest(BaseModel):
    name: str | None = None
    hot_days: int | None = Field(None, ge=1, le=365)
    warm_days: int | None = Field(None, ge=1, le=1825)
    cold_days: int | None = Field(None, ge=1, le=3650)
    is_active: bool | None = None
