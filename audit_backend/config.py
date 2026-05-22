from pydantic_settings import BaseSettings


class AuditSettings(BaseSettings):
    db_host: str = "postgres"
    db_port: int = 5432
    db_user: str = "madf_audit_ro"
    db_password: str = "madf_audit_ro"
    db_name: str = "madf"

    redis_host: str = "redis"
    redis_port: int = 6379

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 240

    default_admin_username: str = "admin"
    default_admin_password: str = "audit123"

    allowed_ips: str = "10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"

    archive_path: str = "/var/audit/archives"
    retention_hot_days: int = 90
    retention_warm_days: int = 365

    model_config = {"env_prefix": "AUDIT_", "extra": "ignore"}


settings = AuditSettings()
