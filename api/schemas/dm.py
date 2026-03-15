from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class DMThreadCreate(BaseModel):
    receiver_id: int


class DMMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class DMThreadResponse(BaseModel):
    id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class DMMessageResponse(BaseModel):
    id: int
    content: str
    is_mine: bool = False
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True