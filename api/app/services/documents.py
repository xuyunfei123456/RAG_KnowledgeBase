from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.lightrag.engine import delete_by_filename
from app.models import Document, new_id
from app.parse.mineru import MinerUError, ensure_ready
from app.repositories import documents as documents_repo
from app.services.errors import (
    ConflictError,
    InternalError,
    NotConfiguredError,
    NotFoundError,
    RejectedError,
)
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

BUSY_DETAIL = "文档正在建库"
DUP_DETAIL = "该空间已有同名文档"


@dataclass(frozen=True)
class OriginalFile:
    path: Path
    filename: str
    media_type: str


async def list_documents(db: AsyncSession, space_id: str) -> list[Document]:
    await get_space(db, space_id)
    return await documents_repo.list_in_space(db, space_id)


async def _accept_file(filename: str | None, payload: bytes) -> tuple[str, str]:
    try:
        name = safe_filename(filename)
    except ValueError as exc:
        raise RejectedError(str(exc)) from exc
    classified = classify_filename(name)
    if classified is None:
        raise RejectedError(REJECT_DETAIL)
    if not payload:
        raise RejectedError("文件是空的")
    kind, _media = classified
    if kind in {"pdf", "docx"}:
        try:
            await ensure_ready()
        except MinerUError as exc:
            raise NotConfiguredError(str(exc)) from exc
    return name, kind


async def _require_idle(db: AsyncSession, space_id: str) -> None:
    rows = await documents_repo.list_in_space(db, space_id)
    if any(row.status == STATUS_PROCESSING for row in rows):
        raise ConflictError(BUSY_DETAIL)


async def _require_unique_filename(
    db: AsyncSession, space_id: str, filename: str, exclude_id: str | None
) -> None:
    other = await documents_repo.get_by_filename(db, space_id, filename)
    if other is not None and other.id != exclude_id:
        raise ConflictError(DUP_DETAIL)


async def _purge_filename(workspace: str, filename: str) -> None:
    try:
        await delete_by_filename(workspace, filename)
    except Exception as exc:
        raise InternalError(str(exc) or "从知识库删除文档失败") from exc


async def upload_document(db: AsyncSession, space_id: str, filename: str | None, payload: bytes) -> Document:
    await get_space(db, space_id)
    name, kind = await _accept_file(filename, payload)
    await _require_unique_filename(db, space_id, name, None)
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


async def replace_document(
    db: AsyncSession, space_id: str, doc_id: str, filename: str | None, payload: bytes
) -> Document:
    space = await get_space(db, space_id)
    row = await documents_repo.get(db, doc_id)
    if row is None or row.space_id != space_id:
        raise NotFoundError("文档不存在")
    await _require_idle(db, space_id)
    name, kind = await _accept_file(filename, payload)
    await _require_unique_filename(db, space_id, name, row.id)
    try:
        stored_path = save_original(space_id, doc_id, name, payload)
    except ValueError as exc:
        raise RejectedError(str(exc)) from exc
    await _purge_filename(space.lightrag_workspace, row.filename)
    remove_parse(space_id, doc_id)
    if row.stored_path != stored_path:
        old = original_abs_path(row.stored_path)
        if old.is_file():
            old.unlink()
    await documents_repo.update_file(
        db,
        row,
        filename=name,
        kind=kind,
        stored_path=stored_path,
        status=STATUS_PROCESSING,
        error_msg=None,
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
    space = await get_space(db, space_id)
    row = await documents_repo.get(db, doc_id)
    if row is None or row.space_id != space_id:
        raise NotFoundError("文档不存在")
    await _require_idle(db, space_id)
    await _purge_filename(space.lightrag_workspace, row.filename)
    stored_path = row.stored_path
    await documents_repo.delete(db, row)
    remove_original(stored_path)
    remove_parse(space_id, doc_id)
