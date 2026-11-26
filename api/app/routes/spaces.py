from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Account
from app.models import KnowledgeSpace
from app.schemas.spaces import CreateSpaceBody, SpaceOut
from app.security import current_account
from app.services import spaces as spaces_service


def space_out(row: KnowledgeSpace) -> SpaceOut:
    return SpaceOut(id=row.id, name=row.name, lightrag_workspace=row.lightrag_workspace)

router = APIRouter(prefix="/api/spaces", tags=["知识空间"])


@router.get("", response_model=list[SpaceOut])
async def list_spaces(
    db: AsyncSession = Depends(get_db),
    _account: Account = Depends(current_account),
):
    rows = await spaces_service.list_spaces(db)
    return [space_out(r) for r in rows]


@router.post("", response_model=SpaceOut)
async def create_space(
    body: CreateSpaceBody,
    db: AsyncSession = Depends(get_db),
    _account: Account = Depends(current_account),
):
    space = await spaces_service.create_space(db, body.name)
    return space_out(space)


@router.delete("/{space_id}")
async def delete_space(
    space_id: str,
    db: AsyncSession = Depends(get_db),
    _account: Account = Depends(current_account),
):
    await spaces_service.delete_space(db, space_id)
    return {"ok": True}
