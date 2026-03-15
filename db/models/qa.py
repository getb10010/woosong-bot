from datetime import datetime
from sqlalchemy import (
    String, DateTime, Boolean, Integer, Text,
    ForeignKey, UniqueConstraint, SmallInteger,
)
from sqlalchemy.orm import Mapped, mapped_column
from db.database import Base


class QAPost(Base):
    __tablename__ = "qa_posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    subject_tag: Mapped[str | None] = mapped_column(String(100))
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)

    report_count: Mapped[int] = mapped_column(Integer, default=0)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class QAAnswer(Base):
    __tablename__ = "qa_answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("qa_posts.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    upvotes: Mapped[int] = mapped_column(Integer, default=0)
    downvotes: Mapped[int] = mapped_column(Integer, default=0)

    report_count: Mapped[int] = mapped_column(Integer, default=0)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class QAVote(Base):
    __tablename__ = "qa_votes"
    __table_args__ = (
        UniqueConstraint("answer_id", "user_id", name="uq_vote_per_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    answer_id: Mapped[int] = mapped_column(ForeignKey("qa_answers.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    vote: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # +1 or -1