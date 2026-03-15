from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from db.database import Base


class Deadline(Base):
    __tablename__ = "deadlines"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(255))
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    scope: Mapped[str] = mapped_column(String(20), nullable=False)  # section | personal
    section: Mapped[str | None] = mapped_column(String(10))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    reminded_3d: Mapped[bool] = mapped_column(Boolean, default=False)
    reminded_1d: Mapped[bool] = mapped_column(Boolean, default=False)
    reminded_3h: Mapped[bool] = mapped_column(Boolean, default=False)

    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)