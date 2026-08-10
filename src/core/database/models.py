from datetime import datetime, timezone
from typing import Any
from sqlalchemy import String, DateTime, Integer, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

class Base(DeclarativeBase):
    pass

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String, unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Quota(Base):
    __tablename__ = "quotas"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    limit_value: Mapped[int] = mapped_column(Integer, default=1000)
    used: Mapped[int] = mapped_column(Integer, default=0)
    reset_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class RateLimit(Base):
    __tablename__ = "rate_limits"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    requests_per_minute: Mapped[int] = mapped_column(Integer, default=60)

class Config(Base):
    __tablename__ = "configs"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB)
