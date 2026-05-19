from typing import Generic, TypeVar

T = TypeVar("T")


class Result(Generic[T]):
    def __init__(self, code: int = 200, message: str = "success", data: T | None = None):
        self.code = code
        self.message = message
        self.data = data

    @staticmethod
    def ok(data: T) -> dict:
        return {"code": 200, "message": "success", "data": data}

    @staticmethod
    def fail(code: int, message: str) -> dict:
        return {"code": code, "message": message, "data": None}
