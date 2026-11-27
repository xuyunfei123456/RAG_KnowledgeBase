from datetime import datetime

from pydantic import BaseModel, Field


class AskBody(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class SourceOut(BaseModel):
    filename: str
    snippet: str
    doc_id: str | None
    page: int | None
    deleted: bool = False


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    sources: list[SourceOut] | None
    created_at: datetime


class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationDetailOut(ConversationOut):
    messages: list[MessageOut]
