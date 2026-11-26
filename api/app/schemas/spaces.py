from pydantic import BaseModel, Field


class CreateSpaceBody(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class SpaceOut(BaseModel):
    id: str
    name: str
    lightrag_workspace: str
