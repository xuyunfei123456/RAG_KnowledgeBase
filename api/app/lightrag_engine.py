# LightRAG Core：图谱 + 向量都落在 PostgreSQL。一个 workspace 一个实例。
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

import numpy as np
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import wrap_embedding_func_with_attrs

from app.config import settings

WORKING_DIR = Path(__file__).resolve().parents[2] / "data" / "lightrag_cache"

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


async def mix_query(workspace: str, question: str) -> dict[str, Any]:
    rag = await get_rag(workspace)
    result = await rag.aquery_llm(
        question,
        param=QueryParam(mode="mix", enable_rerank=False),
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


async def close_all() -> None:
    async with _lock:
        instances = list(_instances.values())
        _instances.clear()
    for rag in instances:
        await rag.finalize_storages()
