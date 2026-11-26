from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.db import get_db
from app.models import Account
from app.schemas.auth import AccountOut, CreateAccountBody, LoginBody
from app.security import current_account
from app.services import accounts as accounts_service

router = APIRouter(tags=["账号"])


@router.post("/api/auth/login", response_model=AccountOut)
async def login(body: LoginBody, request: Request, db: AsyncSession = Depends(get_db)):
    account = await accounts_service.authenticate(db, body.username, body.password)
    request.session["account_id"] = account.id
    return AccountOut(id=account.id, username=account.username)


@router.post("/api/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/api/auth/me", response_model=AccountOut)
async def me(account: Account = Depends(current_account)):
    return AccountOut(id=account.id, username=account.username)


@router.post("/api/accounts", response_model=AccountOut)
async def create_account(
    body: CreateAccountBody,
    db: AsyncSession = Depends(get_db),
    _account: Account = Depends(current_account),
):
    account = await accounts_service.create_account(db, body.username, body.password)
    return AccountOut(id=account.id, username=account.username)
