import uuid

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from audit_backend.core.exceptions import NotFoundException
from audit_backend.models.audit_admin_user import AuditAdminUser
from audit_backend.models.audit_retention_policy import AuditRetentionPolicy

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _admin_to_dict(a: AuditAdminUser) -> dict:
    return {
        "id": str(a.id),
        "username": a.username,
        "display_name": a.display_name,
        "role": a.role,
        "is_active": a.is_active,
        "last_login_at": a.last_login_at.isoformat() if a.last_login_at else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def _policy_to_dict(p: AuditRetentionPolicy) -> dict:
    return {
        "id": str(p.id),
        "name": p.name,
        "hot_days": p.hot_days,
        "warm_days": p.warm_days,
        "cold_days": p.cold_days,
        "is_active": p.is_active,
    }


class SettingsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_admins(self) -> list[dict]:
        stmt = select(AuditAdminUser).order_by(AuditAdminUser.created_at.desc())
        result = await self.session.execute(stmt)
        admins = result.scalars().all()
        return [_admin_to_dict(a) for a in admins]

    async def create_admin(
        self,
        username: str,
        password: str,
        display_name: str | None = None,
        role: str = "auditor",
    ) -> dict:
        admin = AuditAdminUser(
            username=username,
            password_hash=pwd_context.hash(password),
            display_name=display_name,
            role=role,
        )
        self.session.add(admin)
        await self.session.commit()
        await self.session.refresh(admin)
        return {
            "id": str(admin.id),
            "username": admin.username,
            "display_name": admin.display_name,
            "role": admin.role,
            "is_active": admin.is_active,
        }

    async def update_admin(
        self,
        admin_id: uuid.UUID,
        username: str | None = None,
        password: str | None = None,
        display_name: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> dict:
        stmt = select(AuditAdminUser).where(AuditAdminUser.id == admin_id)
        result = await self.session.execute(stmt)
        admin = result.scalar_one_or_none()
        if admin is None:
            raise NotFoundException("管理员不存在")

        if username is not None:
            admin.username = username
        if password is not None:
            admin.password_hash = pwd_context.hash(password)
        if display_name is not None:
            admin.display_name = display_name
        if role is not None:
            admin.role = role
        if is_active is not None:
            admin.is_active = is_active

        await self.session.commit()
        await self.session.refresh(admin)
        return {
            "id": str(admin.id),
            "username": admin.username,
            "display_name": admin.display_name,
            "role": admin.role,
            "is_active": admin.is_active,
        }

    async def delete_admin(self, admin_id: uuid.UUID):
        stmt = select(AuditAdminUser).where(AuditAdminUser.id == admin_id)
        result = await self.session.execute(stmt)
        admin = result.scalar_one_or_none()
        if admin is None:
            raise NotFoundException("管理员不存在")

        admin.is_active = False
        await self.session.commit()

    async def get_retention_policies(self) -> list[dict]:
        stmt = select(AuditRetentionPolicy).order_by(
            AuditRetentionPolicy.created_at.desc()
        )
        result = await self.session.execute(stmt)
        policies = result.scalars().all()
        return [_policy_to_dict(p) for p in policies]

    async def get_retention_policy(self) -> dict:
        from audit_backend.config import settings as app_settings
        return {
            "hot_days": app_settings.retention_hot_days,
            "warm_days": app_settings.retention_warm_days,
            "archive_path": app_settings.archive_path,
        }

    async def update_retention_policy(self, hot_days: int, warm_days: int) -> dict:
        from audit_backend.config import settings as app_settings
        app_settings.retention_hot_days = hot_days
        app_settings.retention_warm_days = warm_days
        return {
            "hot_days": app_settings.retention_hot_days,
            "warm_days": app_settings.retention_warm_days,
            "archive_path": app_settings.archive_path,
        }

    async def update_retention_policy_by_id(
        self,
        policy_id: uuid.UUID,
        name: str | None = None,
        hot_days: int | None = None,
        warm_days: int | None = None,
        cold_days: int | None = None,
        is_active: bool | None = None,
    ) -> dict:
        stmt = select(AuditRetentionPolicy).where(
            AuditRetentionPolicy.id == policy_id
        )
        result = await self.session.execute(stmt)
        policy = result.scalar_one_or_none()
        if policy is None:
            raise NotFoundException("保留策略不存在")

        if name is not None:
            policy.name = name
        if hot_days is not None:
            policy.hot_days = hot_days
        if warm_days is not None:
            policy.warm_days = warm_days
        if cold_days is not None:
            policy.cold_days = cold_days
        if is_active is not None:
            policy.is_active = is_active

        await self.session.commit()
        await self.session.refresh(policy)
        return _policy_to_dict(policy)
