from datetime import datetime, timedelta, timezone

from sqlalchemy import case, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Conversation, Message, new_id


def _turn_times() -> tuple[datetime, datetime]:
    # Postgres now() 是事务开始时间，同一轮两行会撞上；问必须早于答。
    asked = datetime.now(timezone.utc)
    return asked, asked + timedelta(milliseconds=1)


async def list_for_account(
    db: AsyncSession, space_id: str, account_id: str
) -> list[Conversation]:
    rows = (
        await db.scalars(
            select(Conversation)
            .where(Conversation.space_id == space_id, Conversation.account_id == account_id)
            .order_by(Conversation.updated_at.desc())
        )
    ).all()
    return list(rows)


async def list_in_space(db: AsyncSession, space_id: str) -> list[Conversation]:
    rows = (await db.scalars(select(Conversation).where(Conversation.space_id == space_id))).all()
    return list(rows)


async def get(db: AsyncSession, conversation_id: str) -> Conversation | None:
    return await db.get(Conversation, conversation_id)


async def list_messages(db: AsyncSession, conversation_id: str) -> list[Message]:
    rows = (
        await db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(
                Message.created_at,
                case((Message.role == "user", 0), else_=1),
                Message.id,
            )
        )
    ).all()
    return list(rows)


async def insert_new(
    db: AsyncSession,
    *,
    space_id: str,
    account_id: str,
    title: str,
    question: str,
    answer: str,
    sources: list[dict],
) -> Conversation:
    conv = Conversation(id=new_id(), space_id=space_id, account_id=account_id, title=title)
    asked, answered = _turn_times()
    db.add(conv)
    db.add(
        Message(
            id=new_id(),
            conversation_id=conv.id,
            role="user",
            content=question,
            sources=None,
            created_at=asked,
        )
    )
    db.add(
        Message(
            id=new_id(),
            conversation_id=conv.id,
            role="assistant",
            content=answer,
            sources=sources,
            created_at=answered,
        )
    )
    await db.commit()
    await db.refresh(conv)
    return conv


async def add_turn(
    db: AsyncSession,
    conv: Conversation,
    *,
    question: str,
    answer: str,
    sources: list[dict],
) -> None:
    asked, answered = _turn_times()
    conv.updated_at = answered
    db.add(
        Message(
            id=new_id(),
            conversation_id=conv.id,
            role="user",
            content=question,
            sources=None,
            created_at=asked,
        )
    )
    db.add(
        Message(
            id=new_id(),
            conversation_id=conv.id,
            role="assistant",
            content=answer,
            sources=sources,
            created_at=answered,
        )
    )
    await db.commit()
    await db.refresh(conv)


async def delete_in_space(db: AsyncSession, space_id: str) -> None:
    conv_ids = list(
        (await db.scalars(select(Conversation.id).where(Conversation.space_id == space_id))).all()
    )
    if not conv_ids:
        return
    await db.execute(delete(Message).where(Message.conversation_id.in_(conv_ids)))
    await db.execute(delete(Conversation).where(Conversation.id.in_(conv_ids)))
