# HTTP 路由。每个资源一个文件，状态码只在这一层出现。
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.routes import auth, conversations, documents, rag, spaces
from app.services.errors import (
    AuthError,
    ConflictError,
    InternalError,
    NotConfiguredError,
    NotFoundError,
    RejectedError,
)


def mount(app: FastAPI) -> None:
    _map_errors(app)
    app.include_router(auth.router)
    app.include_router(spaces.router)
    app.include_router(documents.router)
    app.include_router(conversations.router)
    app.include_router(rag.router)


def _map_errors(app: FastAPI) -> None:
    mapping: list[tuple[type[Exception], int]] = [
        (AuthError, 401),
        (NotFoundError, 404),
        (ConflictError, 409),
        (RejectedError, 400),
        (NotConfiguredError, 503),
        (InternalError, 500),
    ]
    for exc_type, status in mapping:
        app.add_exception_handler(exc_type, _handler(status))


def _handler(status: int):
    async def handle(_request, exc):
        return JSONResponse(status_code=status, content={"detail": exc.detail})

    return handle
