# 进程启动：建表、引导账号、探活 LightRAG。不含 HTTP。
from sqlalchemy import text

from app.db import Base, SessionLocal, engine
from app.lightrag.engine import apply_postgres_env, close_all, get_rag
from app.services.accounts import ensure_bootstrap_account


async def startup() -> None:
    # 导入模型，让 Base.metadata 带上产品表。
    import app.models  # noqa: F401

    apply_postgres_env()
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as db:
        await ensure_bootstrap_account(db)
    await get_rag("probe")


async def shutdown() -> None:
    await close_all()
