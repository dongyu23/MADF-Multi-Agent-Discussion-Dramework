from enum import IntEnum


class ErrorCode(IntEnum):
    # ── 通用错误 1000-1999 ──
    SUCCESS = 200
    INVALID_PARAMS = 1001
    UNAUTHORIZED = 1002
    FORBIDDEN = 1003
    NOT_FOUND = 1004
    INTERNAL_ERROR = 1999

    # ── 用户模块 2000-2999 ──
    USERNAME_EXISTS = 2001
    PHONE_EXISTS = 2002
    USER_NOT_FOUND = 2003
    WRONG_PASSWORD = 2004

    # ── 角色模块 3000-3999 ──
    SKILL_NOT_FOUND = 3001
    SKILL_GENERATION_FAILED = 3002
    SKILL_IN_USE = 3003
    SKILL_NAME_EXISTS = 3004

    # ── 讨论模块 4000-4999 ──
    DISCUSSION_NOT_FOUND = 4001
    DISCUSSION_ENDED = 4002
    AGENT_NOT_AVAILABLE = 4003

    # ── 审计模块 5000-5999 ──
    AUDIT_QUERY_FAILED = 5001


class BusinessException(Exception):
    """业务异常。接受 ErrorCode 作为构造参数，禁止硬编码错误码数字。"""

    def __init__(self, error_code: ErrorCode, detail: str = ""):
        self.error_code = error_code
        self.detail = detail or error_code.name
        super().__init__(self.detail)
