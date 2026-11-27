# 只 HTTP 调本机 mineru-kit api-server（8001），不把 mineru 装进本仓库。
from __future__ import annotations

import hashlib
import io
import json
import zipfile
from dataclasses import dataclass
from urllib.parse import urljoin

import httpx

from app.config import settings

_POLL_SECONDS = 1.0
_POLL_LIMIT = 600
_HEALTH_TIMEOUT = 5.0
_HTTP_TIMEOUT = httpx.Timeout(120.0, connect=10.0)
_TERMINAL = {"completed", "partial", "failed", "canceled"}


def _base() -> str:
    return settings.mineru_api_url.rstrip("/") + "/"


def _url(path: str) -> str:
    return urljoin(_base(), path.lstrip("/"))


class MinerUError(Exception):
    pass


@dataclass(frozen=True)
class ParsePages:
    # LightRAG 用：每页 Markdown 文本 + file_path（含 #page=n）
    pages: list[tuple[str, str]]
    # 产品自用：原样落盘，不进 LightRAG
    markdown: bytes
    structured: bytes


async def ensure_ready() -> None:
    try:
        async with httpx.AsyncClient(timeout=_HEALTH_TIMEOUT) as client:
            response = await client.get(_url("v1/health"))
    except httpx.RequestError as exc:
        raise MinerUError("连不上本机 MinerU（" + settings.mineru_api_url + "）") from exc
    if response.status_code != 200:
        raise MinerUError("本机 MinerU 未就绪")


def _zip_bytes(archive: zipfile.ZipFile, name: str) -> bytes | None:
    needle = name.lower()
    for info in archive.infolist():
        if info.is_dir():
            continue
        filename = info.filename.replace("\\", "/").rsplit("/", 1)[-1].lower()
        if filename == needle:
            return archive.read(info)
    return None


def _annotation_texts(items: object) -> list[str]:
    if not isinstance(items, list):
        return []
    texts: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        text = (item.get("content") or "").strip()
        if text:
            texts.append(text)
    return texts


def _block_markdown(block: dict) -> str:
    """一块进 LightRAG 的文本。表格把表题、表身、脚注收成一段，不拆开。"""
    body = (block.get("content") or "").strip()
    if (block.get("type") or "").strip() != "table":
        return body
    captions = _annotation_texts(block.get("captions"))
    footnotes = _annotation_texts(block.get("footnotes"))
    return "\n\n".join(part for part in [*captions, body, *footnotes] if part)


def pages_from_structured(payload: dict, filename: str) -> list[tuple[str, str]]:
    pages = payload.get("pages")
    if not isinstance(pages, list) or not pages:
        raise MinerUError("MinerU 结果没有页")
    out: list[tuple[str, str]] = []
    for page in pages:
        if not isinstance(page, dict):
            continue
        idx = int(page.get("page_idx", 0)) + 1
        parts: list[str] = []
        for block in page.get("blocks") or []:
            if not isinstance(block, dict):
                continue
            text = _block_markdown(block)
            if text:
                parts.append(text)
        body = "\n\n".join(parts).strip()
        if body:
            out.append((f"{filename}#page={idx}", body))
    if not out:
        raise MinerUError("MinerU 解析结果是空的")
    return out


async def parse_file(filename: str, payload: bytes) -> ParsePages:
    """提交任务、上传原文件、轮询、解开 ZIP。JSON 不进 LightRAG。"""
    digest = hashlib.sha256(payload).hexdigest()
    body = {
        "files": [
            {
                "file_name": filename,
                "bytes": len(payload),
                "sha256sum": digest,
            }
        ],
        "tier": settings.mineru_tier,
        "ocr_mode": settings.mineru_ocr_mode,
        "output_formats": ["default"],
    }
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT, follow_redirects=False) as client:
            created = await client.post(_url("v1/tasks"), json=body)
            if created.status_code >= 400:
                raise MinerUError(_error_text(created, "创建解析任务失败"))
            task = created.json()
            task_id = task.get("task_id")
            files = task.get("files") or []
            if not task_id or not files:
                raise MinerUError("MinerU 创建任务没有返回 task_id")
            item = files[0]
            upload = item.get("upload")
            if item.get("status") == "waiting-file" and upload and upload.get("url"):
                headers = dict(upload.get("headers") or {})
                headers["Content-Length"] = str(len(payload))
                headers.setdefault("Content-Type", "application/octet-stream")
                put = await client.put(
                    urljoin(_base(), str(upload["url"])),
                    content=payload,
                    headers=headers,
                )
                if put.status_code >= 400:
                    raise MinerUError(_error_text(put, "上传原文件到 MinerU 失败"))
            snapshot = await _poll(client, str(task_id))
            file_item = (snapshot.get("files") or [None])[0]
            if not isinstance(file_item, dict) or file_item.get("status") != "completed":
                raise MinerUError(_task_fail_message(snapshot))
            result_url = file_item.get("result_url")
            if not isinstance(result_url, str) or not result_url:
                raise MinerUError("MinerU 完成但没有 result_url")
            download = await client.get(urljoin(_base(), result_url))
            if download.status_code >= 400:
                raise MinerUError(_error_text(download, "下载 MinerU 结果失败"))
            zip_payload = download.content
    except httpx.RequestError as exc:
        raise MinerUError("连不上本机 MinerU（" + settings.mineru_api_url + "）") from exc
    return _pages_from_zip(zip_payload, filename)


async def _poll(client: httpx.AsyncClient, task_id: str) -> dict:
    url = _url(f"v1/tasks/{task_id}")
    for _ in range(_POLL_LIMIT):
        response = await client.get(url)
        if response.status_code >= 400:
            raise MinerUError(_error_text(response, "查询 MinerU 任务失败"))
        task = response.json()
        status = task.get("status")
        if status in _TERMINAL:
            return task
        await _sleep(_POLL_SECONDS)
    raise MinerUError("MinerU 解析超时")


async def _sleep(seconds: float) -> None:
    import asyncio

    await asyncio.sleep(seconds)


def _pages_from_zip(zip_payload: bytes, filename: str) -> ParsePages:
    try:
        archive = zipfile.ZipFile(io.BytesIO(zip_payload))
    except zipfile.BadZipFile as exc:
        raise MinerUError("MinerU 结果不是 ZIP") from exc
    markdown = _zip_bytes(archive, "markdown.md")
    if markdown is None:
        raise MinerUError("MinerU ZIP 里没有 markdown.md")
    structured = _zip_bytes(archive, "structured_content.json")
    if structured is None:
        raise MinerUError("MinerU ZIP 里没有 structured_content.json")
    try:
        payload = json.loads(structured.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MinerUError("MinerU structured_content.json 无法解析") from exc
    if not isinstance(payload, dict):
        raise MinerUError("MinerU structured_content.json 格式不对")
    if not markdown.decode("utf-8").strip():
        raise MinerUError("MinerU 解析结果是空的")
    # 进 LightRAG 的是每页 Markdown 文本（表格含表题和脚注）；JSON 只当页索引。
    pages = pages_from_structured(payload, filename)
    return ParsePages(pages=pages, markdown=markdown, structured=structured)


def _error_text(response: httpx.Response, fallback: str) -> str:
    try:
        body = response.json()
    except ValueError:
        return fallback
    detail = body.get("message") or body.get("detail") or body.get("error")
    if isinstance(detail, str) and detail.strip():
        return detail.strip()
    return fallback


def _task_fail_message(task: dict) -> str:
    files = task.get("files") or []
    item = files[0] if files else {}
    for source in (item, task):
        if not isinstance(source, dict):
            continue
        for key in ("error", "message", "detail"):
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    status = task.get("status")
    return "MinerU 解析失败" + (f"（{status}）" if status else "")
