from sqlalchemy.ext.asyncio import AsyncSession

from app.lightrag.engine import forget_workspace
from app.models import KnowledgeSpace
from app.repositories import documents as documents_repo
from app.repositories import spaces as spaces_repo
from app.services.errors import NotFoundError
from app.storage.originals import remove_space_originals
from app.storage.parses import remove_space_parses


async def list_spaces(db: AsyncSession) -> list[KnowledgeSpace]:
    return await spaces_repo.list_all(db)


async def get_space(db: AsyncSession, space_id: str) -> KnowledgeSpace:
    space = await spaces_repo.get(db, space_id)
    if space is None:
        raise NotFoundError("知识空间不存在")
    return space


async def create_space(db: AsyncSession, name: str) -> KnowledgeSpace:
    return await spaces_repo.insert(db, name.strip())


async def delete_space(db: AsyncSession, space_id: str) -> None:
    space = await get_space(db, space_id)
    workspace = space.lightrag_workspace
    await documents_repo.delete_in_space(db, space_id)
    await spaces_repo.delete(db, space)
    remove_space_originals(space_id)
    remove_space_parses(space_id)
    await forget_workspace(workspace)
