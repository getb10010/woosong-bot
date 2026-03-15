from pydantic import BaseModel, Field
from enum import Enum


class ReportCategory(str, Enum):
    spam = "spam"
    harassment = "harassment"
    inappropriate = "inappropriate"
    other = "other"


class ReportCreate(BaseModel):
    message_id: int
    category: ReportCategory