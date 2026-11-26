# 密码哈希与当前登录账号。
import hashlib
import hmac
import os

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Account
from app.repositories import accounts as accounts_repo


def hash_password(plain: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, 200_000)
    return salt.hex() + ":" + digest.hex()


def verify_password(plain: str, stored: str) -> bool:
    salt_hex, digest_hex = stored.split(":", 1)
    salt = bytes.fromhex(salt_hex)
    expected = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, 200_000)
    return hmac.compare_digest(expected.hex(), digest_hex)


async def current_account(request: Request, db: AsyncSession = Depends(get_db)) -> Account:
    account_id = request.session.get("account_id")
    if not account_id:
        raise HTTPException(status_code=401, detail="未登录")
    account = await accounts_repo.get_by_id(db, account_id)
    if account is None:
        request.session.clear()
        raise HTTPException(status_code=401, detail="未登录")
    return account
