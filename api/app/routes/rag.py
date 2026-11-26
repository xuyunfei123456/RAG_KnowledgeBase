from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.rag import RagInsertBody, RagQueryBody
from app.services import rag as rag_service

router = APIRouter(prefix="/api/rag", tags=["检索"])


@router.get("/health")
async def rag_health(db: AsyncSession = Depends(get_db)):
    return await rag_service.health(db)


@router.post("/insert")
async def rag_insert(body: RagInsertBody):
    track_id = await rag_service.insert(body.workspace, body.text, body.file_path)
    return {"ok": True, "workspace": body.workspace, "track_id": track_id}


@router.post("/query")
async def rag_query(body: RagQueryBody):
    result = await rag_service.query(body.workspace, body.question)
    return {"workspace": body.workspace, **result}
