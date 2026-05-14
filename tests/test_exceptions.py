"""Exception handling & response format unit tests."""
import pytest
from backend.core.exceptions import BusinessException, ErrorCode
from backend.core.exception_handlers import _http_status
from backend.core.responses import Result, PageResult


class TestBusinessException:
    def test_creation_with_code(self):
        exc = BusinessException(ErrorCode.USERNAME_EXISTS, "User 'test' already taken")
        assert exc.error_code == ErrorCode.USERNAME_EXISTS
        assert exc.detail == "User 'test' already taken"
        assert str(exc) == "User 'test' already taken"

    def test_creation_default_detail(self):
        exc = BusinessException(ErrorCode.NOT_FOUND)
        assert exc.detail == "NOT_FOUND"

    def test_all_error_codes_distinct(self):
        values = [e.value for e in ErrorCode]
        assert len(values) == len(set(values))

    def test_error_code_ranges(self):
        assert 1000 <= ErrorCode.INVALID_PARAMS < 2000
        assert 2000 <= ErrorCode.USERNAME_EXISTS < 3000
        assert 3000 <= ErrorCode.SKILL_NOT_FOUND < 4000
        assert 4000 <= ErrorCode.DISCUSSION_NOT_FOUND < 5000
        assert 5000 <= ErrorCode.AUDIT_QUERY_FAILED < 6000


class TestHttpStatusMapping:
    @pytest.mark.parametrize("code,expected", [
        (ErrorCode.UNAUTHORIZED, 401),
        (ErrorCode.FORBIDDEN, 403),
        (ErrorCode.NOT_FOUND, 404),
        (ErrorCode.USER_NOT_FOUND, 404),
        (ErrorCode.SKILL_NOT_FOUND, 404),
        (ErrorCode.DISCUSSION_NOT_FOUND, 404),
        (ErrorCode.USERNAME_EXISTS, 409),
        (ErrorCode.PHONE_EXISTS, 409),
        (ErrorCode.SKILL_NAME_EXISTS, 409),
        (ErrorCode.SKILL_IN_USE, 409),
        (ErrorCode.INVALID_PARAMS, 422),
        (ErrorCode.SUCCESS, 400),
        (ErrorCode.INTERNAL_ERROR, 400),
        (ErrorCode.WRONG_PASSWORD, 400),
        (ErrorCode.SKILL_GENERATION_FAILED, 400),
        (ErrorCode.DISCUSSION_ENDED, 400),
        (ErrorCode.AGENT_NOT_AVAILABLE, 400),
        (ErrorCode.AUDIT_QUERY_FAILED, 400),
    ])
    def test_http_status(self, code, expected):
        assert _http_status(code) == expected


class TestResult:
    def test_ok_format(self):
        r = Result.ok({"name": "test"}, message="created")
        d = r.model_dump()
        assert d["code"] == 200
        assert d["message"] == "created"
        assert d["data"] == {"name": "test"}

    def test_ok_default_message(self):
        r = Result.ok("data")
        assert r.message == "success"

    def test_fail_format(self):
        r = Result.fail(code=2001, message="Username exists")
        d = r.model_dump()
        assert d["code"] == 2001
        assert d["message"] == "Username exists"
        assert d["data"] is None


class TestPageResult:
    def test_of_has_more_true(self):
        p = PageResult.of(items=[1, 2, 3], total=20, page=1, page_size=5)
        assert p.has_more is True
        assert p.total == 20

    def test_of_has_more_false_last_page(self):
        p = PageResult.of(items=[1, 2], total=12, page=3, page_size=5)
        assert p.has_more is False

    def test_of_has_more_false_exact(self):
        p = PageResult.of(items=[1, 2, 3, 4, 5], total=5, page=1, page_size=5)
        assert p.has_more is False

    def test_of_has_more_empty(self):
        p = PageResult.of(items=[], total=0, page=1, page_size=20)
        assert p.has_more is False

    def test_of_structure(self):
        p = PageResult.of(items=[1, 2], total=10, page=1, page_size=2)
        d = p.model_dump()
        assert d == {"items": [1, 2], "total": 10, "page": 1, "page_size": 2, "has_more": True}
