class AuditException(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


class UnauthorizedException(AuditException):
    def __init__(self, message: str = "未认证"):
        super().__init__(code=6002, message=message)


class ForbiddenException(AuditException):
    def __init__(self, message: str = "权限不足"):
        super().__init__(code=6003, message=message)


class NotFoundException(AuditException):
    def __init__(self, message: str = "资源不存在"):
        super().__init__(code=6004, message=message)
