# 产品 HTTP API。检索走进程内的 LightRAG Core，存储全在 PostgreSQL。
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request

from app.config import settings
from app.db import Base, SessionLocal, engine, get_db
from app.lightrag_engine import apply_postgres_env, close_all, get_rag, insert_text, mix_query
from app.models import Account, KnowledgeSpace, new_id
from app.security import current_account, hash_password, verify_password


@asynccontextmanager
async def lifespan(_app: FastAPI):
    apply_postgres_env()
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as db:
        exists = await db.scalar(
            select(Account).where(Account.username == settings.bootstrap_username)
        )
        if exists is None:
            db.add(
                Account(
                    username=settings.bootstrap_username,
                    password_hash=hash_password(settings.bootstrap_password),
                )
            )
            await db.commit()
    # 先建 LightRAG 的 PG 表，不调模型。插入和 mix 查询等配好密钥再打。
    await get_rag("probe")
    try:
        yield
    finally:
        await close_all()


app = FastAPI(title="知识空间问答", lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    same_site="lax",
    https_only=False,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginBody(BaseModel):
    username: str
    password: str


class AccountOut(BaseModel):
    id: str
    username: str


class CreateAccountBody(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class CreateSpaceBody(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class SpaceOut(BaseModel):
    id: str
    name: str
    lightrag_workspace: str


@app.post("/api/auth/login", response_model=AccountOut)
async def login(body: LoginBody, request: Request, db: AsyncSession = Depends(get_db)):
    account = await db.scalar(select(Account).where(Account.username == body.username))
    if account is None or not verify_password(body.password, account.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    request.session["account_id"] = account.id
    return AccountOut(id=account.id, username=account.username)


@app.post("/api/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@app.get("/api/auth/me", response_model=AccountOut)
async def me(account: Account = Depends(current_account)):
    return AccountOut(id=account.id, username=account.username)


@app.post("/api/accounts", response_model=AccountOut)
async def create_account(
    body: CreateAccountBody,
    db: AsyncSession = Depends(get_db),
    _account: Account = Depends(current_account),
):
    dup = await db.scalar(select(Account).where(Account.username == body.username))
    if dup is not None:
        raise HTTPException(status_code=409, detail="用户名已存在")
    account = Account(username=body.username, password_hash=hash_password(body.password))
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return AccountOut(id=account.id, username=account.username)


@app.get("/api/spaces", response_model=list[SpaceOut])
async def list_spaces(
    db: AsyncSession = Depends(get_db),
    _account: Account = Depends(current_account),
):
    rows = (await db.scalars(select(KnowledgeSpace).order_by(KnowledgeSpace.created_at))).all()
    return [
        SpaceOut(id=r.id, name=r.name, lightrag_workspace=r.lightrag_workspace)
        for r in rows
    ]


@app.post("/api/spaces", response_model=SpaceOut)
async def create_space(
    body: CreateSpaceBody,
    db: AsyncSession = Depends(get_db),
    _account: Account = Depends(current_account),
):
    space = KnowledgeSpace(
        name=body.name.strip(),
        lightrag_workspace="ws_" + new_id(),
    )
    db.add(space)
    await db.commit()
    await db.refresh(space)
    return SpaceOut(id=space.id, name=space.name, lightrag_workspace=space.lightrag_workspace)


class RagInsertBody(BaseModel):
    workspace: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=1)
    file_path: str | None = None


class RagQueryBody(BaseModel):
    workspace: str = Field(min_length=1, max_length=64)
    question: str = Field(min_length=1)


@app.get("/api/rag/health")
async def rag_health(db: AsyncSession = Depends(get_db)):
    vector_ok = await db.scalar(text("SELECT extversion FROM pg_extension WHERE extname = 'vector'"))
    table_rows = await db.execute(
        text(
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname = 'public' AND tablename LIKE 'lightrag%' "
            "ORDER BY tablename"
        )
    )
    tables = [row[0] for row in table_rows.fetchall()]
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


@app.post("/api/rag/insert")
async def rag_insert(body: RagInsertBody):
    missing = settings.missing_model_config()
    if missing:
        raise HTTPException(status_code=503, detail=missing)
    try:
        track_id = await insert_text(body.workspace, body.text, body.file_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True, "workspace": body.workspace, "track_id": track_id}


@app.post("/api/rag/query")
async def rag_query(body: RagQueryBody):
    missing = settings.missing_model_config()
    if missing:
        raise HTTPException(status_code=503, detail=missing)
    try:
        result = await mix_query(body.workspace, body.question)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"workspace": body.workspace, **result}
