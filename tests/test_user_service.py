"""UserService unit tests — all repositories mocked, no DB needed."""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.services.user.service import UserService
from backend.services.user.schemas import TokenResponse, UserResponse
from backend.core.exceptions import BusinessException, ErrorCode


def make_mock_user(user_id=None, username="testuser", phone=None):
    user = MagicMock()
    user.id = user_id or uuid.uuid4()
    user.username = username
    user.password_hash = "hashed_secret123"
    user.phone = phone
    user.created_at = MagicMock()
    user.created_at.isoformat.return_value = "2024-01-01T00:00:00+00:00"
    return user


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def svc(mock_session):
    repo = MagicMock()
    audit = MagicMock()
    repo.find_by_username = AsyncMock()
    repo.find_by_phone = AsyncMock()
    repo.find_by_id = AsyncMock()
    repo.create = AsyncMock()
    audit.record = AsyncMock()
    svc = UserService.__new__(UserService)
    svc.repo = repo
    svc.audit = audit
    svc.pwd_context = MagicMock()
    svc.pwd_context.hash.return_value = "hashed_secret123"
    svc.pwd_context.verify.return_value = True
    svc._issue_token = UserService(mock_session)._issue_token
    return svc, repo, audit


class TestRegister:
    @pytest.mark.asyncio
    async def test_register_success(self, svc):
        svc_obj, mock_repo, mock_audit = svc
        mock_repo.find_by_username.return_value = None
        mock_repo.find_by_phone.return_value = None
        mock_repo.create.return_value = make_mock_user()

        token, user = await svc_obj.register("newuser", "secret123", None)

        assert isinstance(token, TokenResponse)
        assert isinstance(user, UserResponse)
        assert user.username == "testuser"
        mock_audit.record.assert_called()

    @pytest.mark.asyncio
    async def test_register_username_exists(self, svc):
        svc_obj, mock_repo, _ = svc
        mock_repo.find_by_username.return_value = make_mock_user()

        with pytest.raises(BusinessException) as exc:
            await svc_obj.register("testuser", "secret123", None)
        assert exc.value.error_code == ErrorCode.USERNAME_EXISTS

    @pytest.mark.asyncio
    async def test_register_phone_exists(self, svc):
        svc_obj, mock_repo, _ = svc
        mock_repo.find_by_username.return_value = None
        mock_repo.find_by_phone.return_value = make_mock_user()

        with pytest.raises(BusinessException) as exc:
            await svc_obj.register("newuser", "secret123", "13900000001")
        assert exc.value.error_code == ErrorCode.PHONE_EXISTS


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, svc):
        svc_obj, mock_repo, mock_audit = svc
        user = make_mock_user()
        mock_repo.find_by_username.return_value = user

        token, user_resp = await svc_obj.login("testuser", "secret123")

        assert isinstance(token, TokenResponse)
        assert user_resp.username == "testuser"
        mock_audit.record.assert_called()

    @pytest.mark.asyncio
    async def test_login_user_not_found(self, svc):
        svc_obj, mock_repo, _ = svc
        mock_repo.find_by_username.return_value = None

        with pytest.raises(BusinessException) as exc:
            await svc_obj.login("nouser", "secret123")
        assert exc.value.error_code == ErrorCode.USER_NOT_FOUND

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, svc):
        svc_obj, mock_repo, _ = svc
        svc_obj.pwd_context.verify.return_value = False
        user = make_mock_user()
        mock_repo.find_by_username.return_value = user

        with pytest.raises(BusinessException) as exc:
            await svc_obj.login("testuser", "wrongpassword")
        assert exc.value.error_code == ErrorCode.WRONG_PASSWORD


class TestGetMe:
    @pytest.mark.asyncio
    async def test_get_me_success(self, svc):
        svc_obj, mock_repo, _ = svc
        uid = uuid.uuid4()
        mock_repo.find_by_id.return_value = make_mock_user(user_id=uid)

        user = await svc_obj.get_me(str(uid))
        assert user.username == "testuser"

    @pytest.mark.asyncio
    async def test_get_me_not_found(self, svc):
        svc_obj, mock_repo, _ = svc
        mock_repo.find_by_id.return_value = None

        with pytest.raises(BusinessException) as exc:
            await svc_obj.get_me(str(uuid.uuid4()))
        assert exc.value.error_code == ErrorCode.USER_NOT_FOUND
