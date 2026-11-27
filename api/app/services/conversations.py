from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.lightrag.engine import mix_query
from app.models import Conversation, Document, Message
from app.parse.page_anchor import split_page_anchor
from app.repositories import conversations as conversations_repo
from app.repositories import documents as documents_repo
from app.services.errors import InternalError, NotConfiguredError, NotFoundError, RejectedError
from app.services.spaces import get_space
from app.storage.originals import STATUS_READY

NOT_FOUND_TEXT = "知识库中未找到"
NOT_CONFIGURED_TEXT = "无法生成回答"
TITLE_MAX = 80


def _require_models() -> None:
    if settings.missing_model_config():
        raise NotConfiguredError(NOT_CONFIGURED_TEXT)


def _title_from(question: str) -> str:
    text = " ".join(question.split())
    if len(text) <= TITLE_MAX:
        return text
    return text[:TITLE_MAX]


def _filename_to_id(docs: list[Document]) -> dict[str, str]:
    # list_in_space 已按 created_at 降序，同名取最新一份。
    index: dict[str, str] = {}
    for doc in docs:
        if doc.filename not in index:
            index[doc.filename] = doc.id
    return index


def sources_from_chunks(chunks: list[dict], filename_to_id: dict[str, str]) -> list[dict]:
    sources: list[dict] = []
    for chunk in chunks:
        content = (chunk.get("content") or "").strip()
        if not content:
            continue
        raw = (chunk.get("file_path") or "").strip()
        filename, page = split_page_anchor(raw) if raw else ("", None)
        sources.append(
            {
                "filename": filename,
                "snippet": content,
                "doc_id": filename_to_id.get(filename),
                "page": page,
            }
        )
    return sources


async def _answer(
    workspace: str, filename_to_id: dict[str, str], has_ready: bool, question: str
) -> tuple[str, list[dict]]:
    if not has_ready:
        return NOT_FOUND_TEXT, []
    try:
        result = await mix_query(workspace, question)
    except Exception as exc:
        raise InternalError(str(exc)) from exc
    sources = sources_from_chunks(result.get("chunks") or [], filename_to_id)
    answer = (result.get("answer") or "").strip()
    if not sources or answer == NOT_FOUND_TEXT:
        return NOT_FOUND_TEXT, []
    return answer, sources


async def _ask_context(db: AsyncSession, space_id: str) -> tuple[str, dict[str, str], bool]:
    space = await get_space(db, space_id)
    _require_models()
    docs = await documents_repo.list_in_space(db, space_id)
    has_ready = any(doc.status == STATUS_READY for doc in docs)
    return space.lightrag_workspace, _filename_to_id(docs), has_ready


def _question(raw: str) -> str:
    text = raw.strip()
    if not text:
        raise RejectedError("问题不能为空")
    return text


async def live_doc_ids(db: AsyncSession, space_id: str) -> set[str]:
    rows = await documents_repo.list_in_space(db, space_id)
    return {row.id for row in rows}


async def list_conversations(db: AsyncSession, space_id: str, account_id: str) -> list[Conversation]:
    await get_space(db, space_id)
    return await conversations_repo.list_for_account(db, space_id, account_id)


async def get_conversation(
    db: AsyncSession, space_id: str, conversation_id: str
) -> tuple[Conversation, list[Message]]:
    await get_space(db, space_id)
    conv = await conversations_repo.get(db, conversation_id)
    if conv is None or conv.space_id != space_id:
        raise NotFoundError("对话不存在")
    messages = await conversations_repo.list_messages(db, conv.id)
    return conv, messages


async def start_conversation(
    db: AsyncSession, space_id: str, account_id: str, question: str
) -> tuple[Conversation, list[Message]]:
    question = _question(question)
    workspace, filename_to_id, has_ready = await _ask_context(db, space_id)
    answer, sources = await _answer(workspace, filename_to_id, has_ready, question)
    conv = await conversations_repo.insert_new(
        db,
        space_id=space_id,
        account_id=account_id,
        title=_title_from(question),
        question=question,
        answer=answer,
        sources=sources,
    )
    messages = await conversations_repo.list_messages(db, conv.id)
    return conv, messages


async def add_message(
    db: AsyncSession, space_id: str, conversation_id: str, question: str
) -> tuple[Conversation, list[Message]]:
    question = _question(question)
    conv = await conversations_repo.get(db, conversation_id)
    if conv is None or conv.space_id != space_id:
        await get_space(db, space_id)
        raise NotFoundError("对话不存在")
    workspace, filename_to_id, has_ready = await _ask_context(db, space_id)
    answer, sources = await _answer(workspace, filename_to_id, has_ready, question)
    await conversations_repo.add_turn(db, conv, question=question, answer=answer, sources=sources)
    messages = await conversations_repo.list_messages(db, conv.id)
    return conv, messages
