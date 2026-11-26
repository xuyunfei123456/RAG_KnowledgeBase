# 用 UTF-8 打通插入和 mix 查询，避开 PowerShell 控制台编码。
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://127.0.0.1:8000"
WORKSPACE = "probe-utf8"
TEXT = (
    "知识空间问答系统使用 LightRAG 做图谱加向量检索。"
    "每个知识空间对应一个不可变的 workspace。"
    "第一版凡登录即可进入全部空间。"
)
QUESTION = "第一版知识空间怎么隔离？"


def post(path: str, payload: dict) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} {path}\n{body}") from exc


def main() -> None:
    inserted = post("/api/rag/insert", {"workspace": WORKSPACE, "text": TEXT})
    print(json.dumps(inserted, ensure_ascii=False, indent=2))
    queried = post("/api/rag/query", {"workspace": WORKSPACE, "question": QUESTION})
    print(json.dumps(queried, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
