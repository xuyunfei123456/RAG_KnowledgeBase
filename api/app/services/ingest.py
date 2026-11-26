# 上传后的后台建库：Markdown 原文直接进 LightRAG；PDF/Word 先走本机 MinerU。
from __future__ import annotations

import asyncio
import logging

from app.config import settings
from app.db import SessionLocal
from app.lightrag.engine import insert_texts
from app.parse.mineru import MinerUError, parse_file
from app.repositories import documents as documents_repo
from app.repositories import spaces as spaces_repo
from app.storage.originals import STATUS_FAILED, STATUS_PROCESSING, STATUS_READY, original_abs_path
from app.storage.parses import save_parse

logger = logging.getLogger(__name__)

_ERROR_MAX = 512


def schedule(doc_id: str) -> None:
    asyncio.get_running_loop().create_task(_ingest(doc_id), name="ingest-" + doc_id)


async def _ingest(doc_id: str) -> None:
    try:
        await _ingest_body(doc_id)
    except Exception:
        logger.exception("文档 %s 建库未捕获异常", doc_id)
        await _fail(doc_id, "建库失败")


async def _ingest_body(doc_id: str) -> None:
    async with SessionLocal() as db:
        row = await documents_repo.get(db, doc_id)
        if row is None or row.status != STATUS_PROCESSING:
            return
        space = await spaces_repo.get(db, row.space_id)
        if space is None:
            await documents_repo.update_status(db, row, STATUS_FAILED, "知识空间不存在")
            return
        missing = settings.missing_model_config()
        if missing:
            await documents_repo.update_status(db, row, STATUS_FAILED, missing)
            return
        path = original_abs_path(row.stored_path)
        if not path.is_file():
            await documents_repo.update_status(db, row, STATUS_FAILED, "原文件不存在")
            return
        kind = row.kind
        filename = row.filename
        workspace = space.lightrag_workspace
        space_id = row.space_id
        payload = path.read_bytes()

    try:
        pages = await _pages(kind, filename, payload, space_id, doc_id)
        await insert_texts(
            workspace,
            [text for _name, text in pages],
            [name for name, _text in pages],
        )
    except (MinerUError, UnicodeDecodeError, ValueError) as exc:
        await _fail(doc_id, str(exc))
        return
    except Exception as exc:
        await _fail(doc_id, str(exc))
        return

    async with SessionLocal() as db:
        still = await documents_repo.get(db, doc_id)
        if still is None or still.status != STATUS_PROCESSING:
            return
        await documents_repo.update_status(db, still, STATUS_READY, None)


async def _pages(
    kind: str, filename: str, payload: bytes, space_id: str, doc_id: str
) -> list[tuple[str, str]]:
    if kind == "markdown":
        text = payload.decode("utf-8").strip()
        if not text:
            raise ValueError("文件是空的")
        return [(filename, text)]
    parsed = await parse_file(filename, payload)
    save_parse(space_id, doc_id, parsed.markdown, parsed.structured)
    return parsed.pages


async def _fail(doc_id: str, message: str) -> None:
    async with SessionLocal() as db:
        row = await documents_repo.get(db, doc_id)
        if row is None or row.status != STATUS_PROCESSING:
            return
        await documents_repo.update_status(db, row, STATUS_FAILED, _clip(message))


def _clip(message: str) -> str:
    text = message.strip() or "建库失败"
    if len(text) <= _ERROR_MAX:
        return text
    return text[: _ERROR_MAX - 1]
