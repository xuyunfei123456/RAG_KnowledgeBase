# LightRAG Core：图谱 + 向量都落在 PostgreSQL。一个 workspace 一个实例。
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import numpy as np
from lightrag import LightRAG, QueryParam
from lightrag.base import BaseVectorStorage
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import wrap_embedding_func_with_attrs

from app.config import REPO_ROOT, settings
from app.parse.page_anchor import split_page_anchor

logger = logging.getLogger(__name__)

WORKING_DIR = REPO_ROOT / "data" / "lightrag_cache"

_lock = asyncio.Lock()
_instances: dict[str, LightRAG] = {}
_postgres_env_applied = False


def apply_postgres_env() -> None:
    """把 DATABASE_URL 写进 LightRAG 读取的 POSTGRES_*。只认这一份连接串。"""
    global _postgres_env_applied
    if _postgres_env_applied:
        return
    pg = settings.postgres
    os.environ["POSTGRES_HOST"] = pg["host"]
    os.environ["POSTGRES_PORT"] = pg["port"]
    os.environ["POSTGRES_USER"] = pg["user"]
    os.environ["POSTGRES_PASSWORD"] = pg["password"]
    os.environ["POSTGRES_DATABASE"] = pg["database"]
    _postgres_env_applied = True


def _require_models() -> None:
    missing = settings.missing_model_config()
    if missing:
        raise RuntimeError(missing)


async def _llm(prompt, system_prompt=None, history_messages=None, **kwargs) -> str:
    _require_models()
    if history_messages is None:
        history_messages = []
    return await openai_complete_if_cache(
        settings.llm_model,
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        **kwargs,
    )


@wrap_embedding_func_with_attrs(
    embedding_dim=settings.embedding_dim,
    max_token_size=8192,
    model_name=settings.embedding_model,
)
async def _embed(texts: list[str]) -> np.ndarray:
    _require_models()
    return await openai_embed.func(
        texts,
        model=settings.embedding_model,
        api_key=settings.embedding_api_key,
        base_url=settings.embedding_base_url,
        embedding_dim=settings.embedding_dim,
    )


def _validate_workspace(workspace: str) -> str:
    name = workspace.strip()
    if not name:
        raise ValueError("workspace 不能为空")
    if name.startswith("$"):
        raise ValueError("workspace 不能以 $ 开头")
    return name


async def get_rag(workspace: str) -> LightRAG:
    name = _validate_workspace(workspace)
    async with _lock:
        existing = _instances.get(name)
        if existing is not None:
            return existing
        apply_postgres_env()
        WORKING_DIR.mkdir(parents=True, exist_ok=True)
        rag = LightRAG(
            working_dir=str(WORKING_DIR),
            workspace=name,
            llm_model_name=settings.llm_model,
            llm_model_func=_llm,
            embedding_func=_embed,
            kv_storage="PGKVStorage",
            vector_storage="PGVectorStorage",
            graph_storage="PGTableGraphStorage",
            doc_status_storage="PGDocStatusStorage",
            # 问答缓存按问题键，不随图谱更新；替换/删除后会把旧回答再答出来。
            enable_llm_cache=False,
            addon_params={"language": "Chinese"},
        )
        await rag.initialize_storages()
        _instances[name] = rag
        return rag


async def insert_text(workspace: str, text: str, file_path: str | None = None) -> str:
    rag = await get_rag(workspace)
    kwargs: dict[str, Any] = {}
    if file_path:
        kwargs["file_paths"] = file_path
    return await rag.ainsert(text, **kwargs)


async def insert_texts(workspace: str, texts: list[str], file_paths: list[str]) -> str:
    rag = await get_rag(workspace)
    return await rag.ainsert(texts, file_paths=file_paths)


async def mix_query(workspace: str, question: str) -> dict[str, Any]:
    rag = await get_rag(workspace)
    result = await rag.aquery_llm(
        question,
        param=QueryParam(
            mode="mix",
            enable_rerank=False,
            user_prompt="若检索到的资料不足以回答问题，回答必须且只能是：知识库中未找到",
        ),
    )
    data = result.get("data") or {}
    llm = result.get("llm_response") or {}
    return {
        "status": result.get("status"),
        "answer": llm.get("content", ""),
        "references": data.get("references") or [],
        "chunks": [
            {
                "file_path": c.get("file_path"),
                "content": c.get("content"),
                "reference_id": c.get("reference_id"),
            }
            for c in (data.get("chunks") or [])
        ],
        "entities": [
            {
                "entity_name": e.get("entity_name"),
                "entity_type": e.get("entity_type"),
                "description": e.get("description"),
                "file_path": e.get("file_path"),
            }
            for e in (data.get("entities") or [])
        ],
        "relationships": [
            {
                "src_id": r.get("src_id"),
                "tgt_id": r.get("tgt_id"),
                "description": r.get("description"),
            }
            for r in (data.get("relationships") or [])
        ],
        "metadata": result.get("metadata") or {},
    }


_DOC_PAGE_SIZE = 200


async def _doc_ids_for_filename(rag: LightRAG, filename: str) -> list[str]:
    """产品一份文档对应 Markdown 一行或 PDF/Word 每页一行，用 file_path 文件名对齐。"""
    matched: list[str] = []
    page = 1
    while True:
        rows, total = await rag.doc_status.get_docs_paginated(page=page, page_size=_DOC_PAGE_SIZE)
        for doc_id, status in rows:
            raw = (status.file_path or "").strip()
            name, _page = split_page_anchor(raw) if raw else ("", None)
            if name == filename:
                matched.append(doc_id)
        if not rows or page * _DOC_PAGE_SIZE >= total:
            break
        page += 1
    return matched


async def delete_by_filename(workspace: str, filename: str) -> None:
    """按产品文件名删掉该空间里对应的 LightRAG 文档（含分页）。串行 adelete。"""
    rag = await get_rag(workspace)
    doc_ids = await _doc_ids_for_filename(rag, filename)
    for doc_id in doc_ids:
        result = await rag.adelete_by_doc_id(doc_id)
        if result.status in {"success", "not_found"}:
            continue
        logger.error("adelete_by_doc_id %s: %s %s", doc_id, result.status, result.message)
        raise RuntimeError("从知识库删除文档失败")


async def drop_workspace(workspace: str) -> None:
    """清空该 workspace 在 PostgreSQL 里的图谱 / 向量 / 块，不是 DROP TABLE。"""
    rag = await get_rag(workspace)
    storages = [
        rag.text_chunks,
        rag.full_docs,
        rag.full_entities,
        rag.full_relations,
        rag.entity_chunks,
        rag.relation_chunks,
        rag.entities_vdb,
        rag.relationships_vdb,
        rag.chunks_vdb,
        rag.chunk_entity_relation_graph,
        rag.doc_status,
    ]
    tasks = []
    for storage in storages:
        if storage is None:
            continue
        if isinstance(storage, BaseVectorStorage):
            tasks.append(storage.drop_all_models())
        else:
            tasks.append(storage.drop())
    results = await asyncio.gather(*tasks, return_exceptions=True)
    errors: list[str] = []
    for result in results:
        if isinstance(result, asyncio.CancelledError):
            raise result
        if isinstance(result, BaseException):
            logger.error("drop_workspace %s 失败: %s", workspace, result)
            errors.append(str(result))
            continue
        if isinstance(result, dict) and result.get("status") != "success":
            message = str(result.get("message") or result)
            logger.error("drop_workspace %s 失败: %s", workspace, message)
            errors.append(message)
    if errors:
        raise RuntimeError("清空知识库失败")


async def forget_workspace(workspace: str) -> None:
    async with _lock:
        _instances.pop(workspace, None)


async def close_all() -> None:
    async with _lock:
        instances = list(_instances.values())
        _instances.clear()
    for rag in instances:
        await rag.finalize_storages()
