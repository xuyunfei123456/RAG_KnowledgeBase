from sqlalchemy.ext.asyncio import AsyncSession

from app.lightrag.engine import drop_workspace, forget_workspace
from app.models import KnowledgeSpace
from app.repositories import conversations as conversations_repo
from app.repositories import documents as documents_repo
from app.repositories import spaces as spaces_repo
from app.services.errors import ConflictError, InternalError, NotFoundError
from app.storage.originals import STATUS_PROCESSING, remove_space_originals
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
    docs = await documents_repo.list_in_space(db, space_id)
    if any(row.status == STATUS_PROCESSING for row in docs):
        raise ConflictError("文档正在建库")
    try:
        await drop_workspace(workspace)
    except Exception as exc:
        raise InternalError("清空知识库失败") from exc
    await conversations_repo.delete_in_space(db, space_id)
    await documents_repo.delete_in_space(db, space_id)
    await spaces_repo.delete(db, space)
    remove_space_originals(space_id)
    remove_space_parses(space_id)
    await forget_workspace(workspace)
