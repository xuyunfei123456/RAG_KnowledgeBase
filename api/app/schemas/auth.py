from pydantic import BaseModel, Field


class LoginBody(BaseModel):
    username: str
    password: str


class AccountOut(BaseModel):
    id: str
    username: str


class CreateAccountBody(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)
