from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KnowledgeSpace, new_id


async def list_all(db: AsyncSession) -> list[KnowledgeSpace]:
    rows = (await db.scalars(select(KnowledgeSpace).order_by(KnowledgeSpace.created_at))).all()
    return list(rows)


async def get(db: AsyncSession, space_id: str) -> KnowledgeSpace | None:
    return await db.get(KnowledgeSpace, space_id)


async def insert(db: AsyncSession, name: str) -> KnowledgeSpace:
    space = KnowledgeSpace(name=name, lightrag_workspace="ws_" + new_id())
    db.add(space)
    await db.commit()
    await db.refresh(space)
    return space


async def delete(db: AsyncSession, space: KnowledgeSpace) -> None:
    await db.delete(space)
    await db.commit()
