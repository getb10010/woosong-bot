from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class LFType(str, Enum):
    lost = "lost"
    found = "found"


class LostFoundCreate(BaseModel):
    type: LFType
    description: str = Field(..., min_length=1, max_length=1000)
    location: str = Field(..., min_length=1, max_length=255)
    photo_url: Optional[str] = None


class LostFoundResponse(BaseModel):
    id: int
    type: str
    description: str
    location: str
    photo_url: Optional[str]
    is_resolved: bool
    created_at: datetime

    class Config:
        from_attributes = True