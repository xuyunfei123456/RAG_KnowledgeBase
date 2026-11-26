# MinerU 解析稿只给我们自己用：页索引、以后点来源落到页。不进 LightRAG。
import shutil
from pathlib import Path

from app.config import REPO_ROOT

PARSES_ROOT = REPO_ROOT / "data" / "parses"


def save_parse(space_id: str, doc_id: str, markdown: bytes, structured: bytes) -> Path:
    dest_dir = PARSES_ROOT / space_id / doc_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    (dest_dir / "markdown.md").write_bytes(markdown)
    (dest_dir / "structured_content.json").write_bytes(structured)
    return dest_dir


def parse_dir(space_id: str, doc_id: str) -> Path:
    return PARSES_ROOT / space_id / doc_id


def remove_parse(space_id: str, doc_id: str) -> None:
    dest = parse_dir(space_id, doc_id)
    root = PARSES_ROOT.resolve()
    if dest.is_dir() and dest.resolve() != root and root in dest.resolve().parents:
        shutil.rmtree(dest)


def remove_space_parses(space_id: str) -> None:
    dest = PARSES_ROOT / space_id
    if dest.is_dir():
        shutil.rmtree(dest)
