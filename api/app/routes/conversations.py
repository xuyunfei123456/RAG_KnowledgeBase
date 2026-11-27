from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Account, Conversation, Message
from app.schemas.conversations import (
    AskBody,
    ConversationDetailOut,
    ConversationOut,
    MessageOut,
    SourceOut,
)
from app.security import current_account
from app.services import conversations as conversations_service


def _source_out(item: dict, live_ids: set[str]) -> SourceOut:
    src = SourceOut.model_validate(item)
    deleted = bool(src.doc_id) and src.doc_id not in live_ids
    return src.model_copy(update={"deleted": deleted})


def _message_out(row: Message, live_ids: set[str]) -> MessageOut:
    sources = None
    if row.sources is not None:
        sources = [_source_out(item, live_ids) for item in row.sources]
    return MessageOut(
        id=row.id,
        role=row.role,
        content=row.content,
        sources=sources,
        created_at=row.created_at,
    )


def _detail_out(
    conv: Conversation, messages: list[Message], live_ids: set[str]
) -> ConversationDetailOut:
    return ConversationDetailOut(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[_message_out(m, live_ids) for m in messages],
    )


router = APIRouter(prefix="/api/spaces/{space_id}/conversations", tags=["对话"])


@router.get("", response_model=list[ConversationOut])
async def list_conversations(
    space_id: str,
    db: AsyncSession = Depends(get_db),
    account: Account = Depends(current_account),
):
    rows = await conversations_service.list_conversations(db, space_id, account.id)
    return [
        ConversationOut(id=r.id, title=r.title, created_at=r.created_at, updated_at=r.updated_at)
        for r in rows
    ]


@router.post("", response_model=ConversationDetailOut)
async def start_conversation(
    space_id: str,
    body: AskBody,
    db: AsyncSession = Depends(get_db),
    account: Account = Depends(current_account),
):
    conv, messages = await conversations_service.start_conversation(
        db, space_id, account.id, body.question
    )
    live_ids = await conversations_service.live_doc_ids(db, space_id)
    return _detail_out(conv, messages, live_ids)


@router.get("/{conversation_id}", response_model=ConversationDetailOut)
async def get_conversation(
    space_id: str,
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    _account: Account = Depends(current_account),
):
    conv, messages = await conversations_service.get_conversation(db, space_id, conversation_id)
    live_ids = await conversations_service.live_doc_ids(db, space_id)
    return _detail_out(conv, messages, live_ids)


@router.post("/{conversation_id}/messages", response_model=ConversationDetailOut)
async def add_message(
    space_id: str,
    conversation_id: str,
    body: AskBody,
    db: AsyncSession = Depends(get_db),
    _account: Account = Depends(current_account),
):
    conv, messages = await conversations_service.add_message(
        db, space_id, conversation_id, body.question
    )
    live_ids = await conversations_service.live_doc_ids(db, space_id)
    return _detail_out(conv, messages, live_ids)
