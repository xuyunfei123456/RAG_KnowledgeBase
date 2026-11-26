# 账号、知识空间与文档。lightrag_workspace 一旦写入不再改。
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def new_id() -> str:
    return uuid.uuid4().hex


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class KnowledgeSpace(Base):
    __tablename__ = "knowledge_spaces"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    # 对应 LightRAG 的 workspace，创建后不可变，后加权限时也不用重建图谱。
    lightrag_workspace: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    space_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("knowledge_spaces.id"), nullable=False, index=True
    )
    # 界面上的文件名，打开原文时用这个名字。
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    # pdf / docx / markdown
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    # 相对 data/originals 的路径，创建后不改。
    stored_path: Mapped[str] = mapped_column(String(512), nullable=False)
    # processing / ready / failed。上传后先 processing，后台建库成功或失败再改。
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    error_msg: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
