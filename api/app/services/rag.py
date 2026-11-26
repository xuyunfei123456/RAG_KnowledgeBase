from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.lightrag.engine import insert_text, mix_query
from app.repositories import health as health_repo
from app.services.errors import InternalError, NotConfiguredError


def _require_models() -> None:
    missing = settings.missing_model_config()
    if missing:
        raise NotConfiguredError(missing)


async def health(db: AsyncSession) -> dict[str, Any]:
    vector_ok = await health_repo.pgvector_version(db)
    tables = await health_repo.lightrag_table_names(db)
    pg = settings.postgres
    return {
        "postgres": {
            "host": pg["host"],
            "port": pg["port"],
            "database": pg["database"],
            "pgvector": vector_ok,
        },
        "lightrag": {
            "workspace": "probe",
            "graph_storage": "PGTableGraphStorage",
            "vector_storage": "PGVectorStorage",
            "tables": list(tables),
        },
        "model_configured": settings.models_ready,
        "llm": {
            "configured": settings.llm_ready,
            "model": settings.llm_model,
            "base_url": settings.llm_base_url,
        },
        "embedding": {
            "configured": settings.embedding_ready,
            "model": settings.embedding_model,
            "base_url": settings.embedding_base_url,
            "dim": settings.embedding_dim,
        },
    }


async def insert(workspace: str, text: str, file_path: str | None) -> str:
    _require_models()
    try:
        return await insert_text(workspace, text, file_path)
    except Exception as exc:
        raise InternalError(str(exc)) from exc


async def query(workspace: str, question: str) -> dict[str, Any]:
    _require_models()
    try:
        return await mix_query(workspace, question)
    except Exception as exc:
        raise InternalError(str(exc)) from exc
