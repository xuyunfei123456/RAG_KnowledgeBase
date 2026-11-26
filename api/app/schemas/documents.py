from datetime import datetime

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: str
    filename: str
    kind: str
    status: str
    error_msg: str | None
    created_at: datetime
