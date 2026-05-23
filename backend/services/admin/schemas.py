
from pydantic import BaseModel, Field

# ═══════════════════════════════════════════
# User Management
# ═══════════════════════════════════════════

class UserAdminItem(BaseModel):
    id: str
    username: str
    phone: str | None = None
    status: str = "active"
    character_count: int = 0
    discussion_count: int = 0
    registered_at: str


class UserTokenUsageSummary(BaseModel):
    total_llm_events: int = 0
    by_type: dict = {}

class UserAdminDetail(UserAdminItem):
    token_usage_summary: UserTokenUsageSummary | None = None
    last_active: str | None = None


class UserAdminListResponse(BaseModel):
    items: list[UserAdminItem]
    total: int
    page: int
    page_size: int
    has_more: bool


class UpdateUserStatusRequest(BaseModel):
    status: str = Field(..., pattern="^(active|disabled)$")


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    phone: str | None = None


class UpdateUsernameRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=128)


class UpdatePhoneRequest(BaseModel):
    phone: str = Field(..., min_length=1, max_length=32)


# ═══════════════════════════════════════════
# Discussion Monitoring
# ═══════════════════════════════════════════

class DiscussionAdminItem(BaseModel):
    id: str
    owner_id: str
    owner_username: str = ""
    topic: str
    status: str
    agent_count: int = 0
    message_count: int = 0
    round_count: int = 0
    token_usage: int = 0
    duration: int = 0
    created_at: str
    started_at: str | None = None
    ended_at: str | None = None


class DiscussionAgentInfo(BaseModel):
    id: str
    skill_id: str
    skill_name: str


class DiscussionMessageInfo(BaseModel):
    id: str
    round_number: int
    agent_name: str | None = None
    message_type: str
    content: str
    confidence: float | None = None
    created_at: str


class DiscussionAdminDetail(DiscussionAdminItem):
    agents: list[DiscussionAgentInfo] = []
    messages: list[DiscussionMessageInfo] = []


class DiscussionAdminListResponse(BaseModel):
    items: list[DiscussionAdminItem]
    total: int
    page: int
    page_size: int
    has_more: bool


class DiscussionTokenUsageResponse(BaseModel):
    discussion_id: str
    total_events: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    llm_call_count: int = 0
    by_type: dict = {}


# ═══════════════════════════════════════════
# Character Management
# ═══════════════════════════════════════════

class CharacterAdminItem(BaseModel):
    id: str
    owner_id: str
    name: str
    description: str
    tags: list[str] | None = None
    is_public: bool
    status: str
    source_count: int | None = None
    model_count: int | None = None
    created_at: str


class CharacterAdminDetail(CharacterAdminItem):
    owner_username: str = ""
    discussion_count: int = 0
    file_path: str = ""


class CharacterAdminListResponse(BaseModel):
    items: list[CharacterAdminItem]
    total: int
    page: int
    page_size: int
    has_more: bool


class UpdateCharacterVisibilityRequest(BaseModel):
    is_public: bool


# ═══════════════════════════════════════════
# Gallery Management
# ═══════════════════════════════════════════

class GalleryAdminItem(BaseModel):
    id: str
    owner_id: str
    owner_username: str
    name: str
    description: str
    tags: list[str] | None = None
    created_at: str


class GalleryAdminListResponse(BaseModel):
    items: list[GalleryAdminItem]
    total: int
    page: int
    page_size: int
    has_more: bool


# ═══════════════════════════════════════════
# Audit & Trace
# ═══════════════════════════════════════════

class AuditEventItem(BaseModel):
    id: str
    discussion_id: str | None = None
    user_id: str | None = None
    event_type: str
    level: str
    payload: dict
    created_at: str


class AuditEventListResponse(BaseModel):
    items: list[AuditEventItem]
    total: int | None = None
    page: int = 1
    page_size: int
    has_more: bool


class OperationAuditItem(BaseModel):
    id: str
    event_type: str
    level: str
    admin_id: str | None = None
    admin_username: str | None = None
    payload: dict
    created_at: str


class OperationAuditListResponse(BaseModel):
    items: list[OperationAuditItem]
    total: int | None = None
    page: int = 1
    page_size: int
    has_more: bool


# ═══════════════════════════════════════════
# System Health
# ═══════════════════════════════════════════

class ComponentStatus(BaseModel):
    status: str  # healthy | degraded | unhealthy
    latency_ms: float | None = None
    error: str | None = None


class HealthOverview(BaseModel):
    app: str
    version: str
    uptime_seconds: float
    components: dict[str, ComponentStatus]


class HealthErrorItem(BaseModel):
    id: str
    event_type: str
    level: str
    message: str
    payload: dict | None = None
    created_at: str


class HealthErrorListResponse(BaseModel):
    items: list[HealthErrorItem]
    page: int
    page_size: int
    total: int | None = None
    has_more: bool


class HealthLoadInfo(BaseModel):
    cpu_percent: float
    memory_percent: float
    db_pool_size: int
    db_pool_checked_out: int
    active_discussions: int
    sse_connections: int
    thread_count: int


class OrphanDiscussion(BaseModel):
    discussion_id: str
    topic: str
    owner_id: str
    status: str
    created_at: str


# ═══════════════════════════════════════════
# Stats
# ═══════════════════════════════════════════

class StatsOverview(BaseModel):
    total_users: int
    total_characters: int
    total_discussions: int
    active_discussions: int
    online_users: int
    total_messages: int
    total_audit_events: int
    p0_errors_today: int = 0
    api_calls_today: int = 0


class TokenUsageSummary(BaseModel):
    discussion_tokens: int = 0
    character_tokens: int = 0
    other_tokens: int = 0
    total_tokens: int = 0
    period: str = "7d"
    by_event_type: dict = {}


class TokenTrendPoint(BaseModel):
    date: str
    llm_tokens: int = 0
    tavily_tokens: int = 0
    other_tokens: int = 0


# ═══════════════════════════════════════════
# Admin Management
# ═══════════════════════════════════════════

class AdminUserItem(BaseModel):
    id: str
    username: str
    display_name: str | None = None
    role: str  # super_admin | admin | auditor
    is_active: bool = True
    last_login: str | None = None
    created_at: str


class CreateAdminRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str | None = None
    role: str = Field(default="admin", pattern="^(super_admin|admin|auditor)$")


class UpdateAdminRequest(BaseModel):
    username: str | None = Field(default=None, min_length=2, max_length=64)
    password: str | None = Field(default=None, min_length=6, max_length=128)
    display_name: str | None = None
    role: str | None = Field(default=None, pattern="^(super_admin|admin|auditor)$")
    is_active: bool | None = None


# ═══════════════════════════════════════════
# Settings
# ═══════════════════════════════════════════

class RetentionPolicyItem(BaseModel):
    id: str
    name: str
    level: str
    hot_days: int
    warm_days: int
    archive_enabled: bool = True
    archive_method: str = "delete"
    is_active: bool = True
    created_at: str | None = None
    updated_at: str | None = None


class SettingsResponse(BaseModel):
    app_name: str
    debug: bool
    cors_origins: str | None = None
    jwt_expire_minutes: int
    llm_api_base: str
    llm_model: str
    db_host: str
    db_port: int
    db_name: str
    redis_host: str
    redis_port: int
    max_discussion_duration: int
    max_agents_per_discussion: int
    retention_days: int
    registration_open: bool
    retention_policies: list[RetentionPolicyItem] = []


class UpdateSettingsRequest(BaseModel):
    debug: bool | None = None
    cors_origins: str | None = None
    jwt_expire_minutes: int | None = Field(default=None, ge=1, le=10080)
    max_discussion_duration: int | None = Field(default=None, ge=60, le=86400)
    max_agents_per_discussion: int | None = Field(default=None, ge=1, le=20)
    retention_days: int | None = Field(default=None, ge=1, le=365)
    registration_open: bool | None = None


class RestartResponse(BaseModel):
    message: str
    docker_available: bool


class UpdateRetentionRequest(BaseModel):
    retention_days: int = Field(..., ge=1, le=365)
    dry_run: bool = False
