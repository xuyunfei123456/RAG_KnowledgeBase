from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Account
from app.repositories import accounts as accounts_repo
from app.security import hash_password, verify_password
from app.services.errors import AuthError, ConflictError


async def authenticate(db: AsyncSession, username: str, password: str) -> Account:
    account = await accounts_repo.get_by_username(db, username)
    if account is None or not verify_password(password, account.password_hash):
        raise AuthError("用户名或密码错误")
    return account


async def create_account(db: AsyncSession, username: str, password: str) -> Account:
    dup = await accounts_repo.get_by_username(db, username)
    if dup is not None:
        raise ConflictError("用户名已存在")
    return await accounts_repo.insert(db, username, hash_password(password))


async def ensure_bootstrap_account(db: AsyncSession) -> None:
    exists = await accounts_repo.get_by_username(db, settings.bootstrap_username)
    if exists is None:
        await accounts_repo.insert(
            db,
            settings.bootstrap_username,
            hash_password(settings.bootstrap_password),
        )
