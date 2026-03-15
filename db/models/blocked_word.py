from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from db.database import Base


class BlockedWord(Base):
    __tablename__ = "blocked_words"

    id: Mapped[int] = mapped_column(primary_key=True)
    word: Mapped[str] = mapped_column(String(255), nullable=False)
    lang: Mapped[str | None] = mapped_column(String(3))
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # block | alert

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)