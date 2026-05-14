from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Result(BaseModel, Generic[T]):
    """统一响应类型。所有 API 返回必须使用此类。"""

    code: int
    message: str = "success"
    data: T | None = None

    @classmethod
    def ok(cls, data: T, message: str = "success") -> "Result[T]":
        return cls(code=200, message=message, data=data)

    @classmethod
    def fail(cls, code: int, message: str) -> "Result[None]":
        return cls(code=code, message=message, data=None)


class PageResult(BaseModel, Generic[T]):
    """分页响应类型。"""

    items: list[T]
    total: int
    page: int
    page_size: int
    has_more: bool

    @classmethod
    def of(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PageResult[T]":
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total,
        )
