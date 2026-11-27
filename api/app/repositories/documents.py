from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document


async def list_in_space(db: AsyncSession, space_id: str) -> list[Document]:
    rows = (
        await db.scalars(
            select(Document).where(Document.space_id == space_id).order_by(Document.created_at.desc())
        )
    ).all()
    return list(rows)


async def get(db: AsyncSession, doc_id: str) -> Document | None:
    return await db.get(Document, doc_id)


async def get_by_filename(db: AsyncSession, space_id: str, filename: str) -> Document | None:
    return await db.scalar(
        select(Document).where(Document.space_id == space_id, Document.filename == filename)
    )


async def insert(
    db: AsyncSession,
    *,
    doc_id: str,
    space_id: str,
    filename: str,
    kind: str,
    stored_path: str,
    status: str,
) -> Document:
    row = Document(
        id=doc_id,
        space_id=space_id,
        filename=filename,
        kind=kind,
        stored_path=stored_path,
        status=status,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def update_status(db: AsyncSession, row: Document, status: str, error_msg: str | None) -> None:
    row.status = status
    row.error_msg = error_msg
    await db.commit()
    await db.refresh(row)


async def update_file(
    db: AsyncSession,
    row: Document,
    *,
    filename: str,
    kind: str,
    stored_path: str,
    status: str,
    error_msg: str | None,
) -> None:
    row.filename = filename
    row.kind = kind
    row.stored_path = stored_path
    row.status = status
    row.error_msg = error_msg
    await db.commit()
    await db.refresh(row)


async def delete(db: AsyncSession, row: Document) -> None:
    await db.delete(row)
    await db.commit()


async def delete_in_space(db: AsyncSession, space_id: str) -> None:
    rows = await list_in_space(db, space_id)
    for row in rows:
        await db.delete(row)
