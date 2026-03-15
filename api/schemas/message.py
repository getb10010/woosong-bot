from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    reply_to_id: Optional[int] = None


class MessageResponse(BaseModel):
    id: int
    content: str
    reply_to_id: Optional[int]
    report_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class MessageAdminResponse(MessageResponse):
    user_id: int
    view_count: int
    is_hidden: bool
    hidden_reason: Optional[str]