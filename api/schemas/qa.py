from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class QAPostCreate(BaseModel):
    question: str = Field(..., min_length=1, max_length=3000)
    subject_tag: Optional[str] = None
    is_anonymous: bool = False


class QAAnswerCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=3000)
    is_anonymous: bool = False


class QAPostResponse(BaseModel):
    id: int
    question: str
    subject_tag: Optional[str]
    is_anonymous: bool
    is_resolved: bool
    username: Optional[str] = None
    created_at: datetime
    answer_count: int = 0

    class Config:
        from_attributes = True


class QAAnswerResponse(BaseModel):
    id: int
    content: str
    is_anonymous: bool
    upvotes: int
    downvotes: int
    username: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class VoteCreate(BaseModel):
    vote: int = Field(..., ge=-1, le=1)  # -1 or +1