from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, new_id
from app.parse.mineru import MinerUError, ensure_ready
from app.repositories import documents as documents_repo
from app.services.errors import NotConfiguredError, NotFoundError, RejectedError
from app.services.ingest import schedule
from app.services.spaces import get_space
from app.storage.originals import (
    REJECT_DETAIL,
    STATUS_PROCESSING,
    classify_filename,
    media_type_for,
    original_abs_path,
    remove_original,
    safe_filename,
    save_original,
)
from app.storage.parses import remove_parse


@dataclass(frozen=True)
class OriginalFile:
    path: Path
    filename: str
    media_type: str


async def list_documents(db: AsyncSession, space_id: str) -> list[Document]:
    await get_space(db, space_id)
    return await documents_repo.list_in_space(db, space_id)


async def upload_document(db: AsyncSession, space_id: str, filename: str | None, payload: bytes) -> Document:
    await get_space(db, space_id)
    try:
        name = safe_filename(filename)
    except ValueError as exc:
        raise RejectedError(str(exc)) from exc
    classified = classify_filename(name)
    if classified is None:
        raise RejectedError(REJECT_DETAIL)
    kind, _media = classified
    if kind in {"pdf", "docx"}:
        try:
            await ensure_ready()
        except MinerUError as exc:
            raise NotConfiguredError(str(exc)) from exc
    doc_id = new_id()
    try:
        stored_path = save_original(space_id, doc_id, name, payload)
    except ValueError as exc:
        raise RejectedError(str(exc)) from exc
    row = await documents_repo.insert(
        db,
        doc_id=doc_id,
        space_id=space_id,
        filename=name,
        kind=kind,
        stored_path=stored_path,
        status=STATUS_PROCESSING,
    )
    schedule(row.id)
    return row


async def get_original(db: AsyncSession, space_id: str, doc_id: str) -> OriginalFile:
    await get_space(db, space_id)
    row = await documents_repo.get(db, doc_id)
    if row is None or row.space_id != space_id:
        raise NotFoundError("文档不存在")
    path = original_abs_path(row.stored_path)
    if not path.is_file():
        raise NotFoundError("原文件不存在")
    return OriginalFile(path=path, filename=row.filename, media_type=media_type_for(row.kind))


async def delete_document(db: AsyncSession, space_id: str, doc_id: str) -> None:
    await get_space(db, space_id)
    row = await documents_repo.get(db, doc_id)
    if row is None or row.space_id != space_id:
        raise NotFoundError("文档不存在")
    stored_path = row.stored_path
    await documents_repo.delete(db, row)
    remove_original(stored_path)
    remove_parse(space_id, doc_id)
