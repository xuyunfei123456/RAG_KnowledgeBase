from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Account
from app.models import Document
from app.schemas.documents import DocumentOut
from app.security import current_account
from app.services import documents as documents_service


def document_out(row: Document) -> DocumentOut:
    return DocumentOut(
        id=row.id,
        filename=row.filename,
        kind=row.kind,
        status=row.status,
        error_msg=row.error_msg,
        created_at=row.created_at,
    )

router = APIRouter(prefix="/api/spaces/{space_id}/documents", tags=["文档"])


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    space_id: str,
    db: AsyncSession = Depends(get_db),
    _account: Account = Depends(current_account),
):
    rows = await documents_service.list_documents(db, space_id)
    return [document_out(r) for r in rows]


@router.post("", response_model=DocumentOut)
async def upload_document(
    space_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _account: Account = Depends(current_account),
):
    payload = await file.read()
    row = await documents_service.upload_document(db, space_id, file.filename, payload)
    return document_out(row)


@router.get("/{doc_id}/original")
async def get_original(
    space_id: str,
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    _account: Account = Depends(current_account),
):
    original = await documents_service.get_original(db, space_id, doc_id)
    return FileResponse(
        original.path,
        media_type=original.media_type,
        filename=original.filename,
        content_disposition_type="inline",
    )


@router.put("/{doc_id}", response_model=DocumentOut)
async def replace_document(
    space_id: str,
    doc_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _account: Account = Depends(current_account),
):
    payload = await file.read()
    row = await documents_service.replace_document(db, space_id, doc_id, file.filename, payload)
    return document_out(row)


@router.delete("/{doc_id}")
async def delete_document(
    space_id: str,
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    _account: Account = Depends(current_account),
):
    await documents_service.delete_document(db, space_id, doc_id)
    return {"ok": True}
