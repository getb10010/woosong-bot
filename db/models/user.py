from datetime import datetime, time
from sqlalchemy import (
    BigInteger, String, Boolean, Integer, Float,
    Time, DateTime, ARRAY, Text,
)
from sqlalchemy.orm import Mapped, mapped_column
from db.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(255))

    section: Mapped[str | None] = mapped_column(String(10))
    gender: Mapped[str | None] = mapped_column(String(20))
    anon_dm_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    quiet_start: Mapped[time | None] = mapped_column(Time, default=time(23, 0))
    quiet_end: Mapped[time | None] = mapped_column(Time, default=time(8, 0))
    lang: Mapped[str] = mapped_column(String(3), default="kz")

    # Notification preferences
    notify_class: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_break: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_deadline: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_exam: Mapped[bool] = mapped_column(Boolean, default=True)
    exam_notify_days: Mapped[int] = mapped_column(Integer, default=7)

    # Tags
    tags: Mapped[list | None] = mapped_column(ARRAY(String), default=[])

    # Moderation
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    ban_until: Mapped[datetime | None] = mapped_column(DateTime)
    ban_reason: Mapped[str | None] = mapped_column(Text)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    auto_hide_count: Mapped[int] = mapped_column(Integer, default=0)
    report_credibility: Mapped[float] = mapped_column(Float, default=1.0)

    # Status
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )