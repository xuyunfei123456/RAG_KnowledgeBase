from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account


async def get_by_id(db: AsyncSession, account_id: str) -> Account | None:
    return await db.get(Account, account_id)


async def get_by_username(db: AsyncSession, username: str) -> Account | None:
    return await db.scalar(select(Account).where(Account.username == username))


async def insert(db: AsyncSession, username: str, password_hash: str) -> Account:
    account = Account(username=username, password_hash=password_hash)
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account
