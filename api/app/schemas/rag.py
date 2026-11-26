from pydantic import BaseModel, Field


class RagInsertBody(BaseModel):
    workspace: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=1)
    file_path: str | None = None


class RagQueryBody(BaseModel):
    workspace: str = Field(min_length=1, max_length=64)
    question: str = Field(min_length=1)
