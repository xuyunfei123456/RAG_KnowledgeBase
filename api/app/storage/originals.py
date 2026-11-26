# 文档类型校验与原文件落地。不解析正文，不调用 pypdf / python-docx。
import shutil
from pathlib import Path

from app.config import REPO_ROOT

ORIGINALS_ROOT = REPO_ROOT / "data" / "originals"

STATUS_PROCESSING = "processing"
STATUS_READY = "ready"
STATUS_FAILED = "failed"

REJECT_DETAIL = "只接受 PDF、Word、Markdown"

# 扩展名 -> (kind, 下载用的 Content-Type)
_KINDS: dict[str, tuple[str, str]] = {
    ".pdf": ("pdf", "application/pdf"),
    ".docx": ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ".md": ("markdown", "text/markdown; charset=utf-8"),
    ".markdown": ("markdown", "text/markdown; charset=utf-8"),
}


def safe_filename(raw: str | None) -> str:
    name = Path(raw or "").name.strip()
    if not name or name in {".", ".."}:
        raise ValueError("文件名无效")
    return name


def classify_filename(filename: str) -> tuple[str, str] | None:
    suffix = Path(filename).suffix.lower()
    return _KINDS.get(suffix)


def media_type_for(kind: str) -> str:
    for k, mime in _KINDS.values():
        if k == kind:
            return mime
    return "application/octet-stream"


def save_original(space_id: str, doc_id: str, filename: str, payload: bytes) -> str:
    """把原文件写到 data/originals/{空间}/{文档id}/文件名，返回相对路径。"""
    if not payload:
        raise ValueError("文件是空的")
    dest_dir = ORIGINALS_ROOT / space_id / doc_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename
    dest.write_bytes(payload)
    return Path(space_id, doc_id, filename).as_posix()


def original_abs_path(stored_path: str) -> Path:
    rel = Path(stored_path)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("存储路径无效")
    return ORIGINALS_ROOT / rel


def remove_original(stored_path: str) -> None:
    dest = original_abs_path(stored_path).parent
    root = ORIGINALS_ROOT.resolve()
    if dest.is_dir() and dest.resolve() != root and root in dest.resolve().parents:
        shutil.rmtree(dest)


def remove_space_originals(space_id: str) -> None:
    dest = ORIGINALS_ROOT / space_id
    if dest.is_dir():
        shutil.rmtree(dest)
