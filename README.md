# RAG 知识库

Python 环境和依赖只用 **uv**，不要用 pip / conda。依赖声明在 `pyproject.toml`，锁定版本在 `uv.lock`。

## 启动服务

1. 打开 Electerm SSH 隧道，让本机 `127.0.0.1:5432` 能连上远端 PostgreSQL（库名 / 用户 / 密码均为 `rag`）。
2. 仓库根目录复制 `.env.example` 为 `.env`，填好 `DATABASE_URL` 以及生成模型、embedding 两套供应商配置（密钥和地址不要混用）。
3. 在仓库根目录执行：

```powershell
uv sync
uv run uvicorn --app-dir api app.main:app --host 127.0.0.1 --port 8000
```

服务地址：http://127.0.0.1:8000  
健康检查：http://127.0.0.1:8000/api/rag/health

改 `.env` 后需要停掉再启动一次。不要用 `python -m uvicorn` 或直接调用 `.venv\Scripts\python.exe`。

## 查看已安装依赖

在仓库根目录：

```powershell
uv tree
uv pip list
```

`uv tree` 看依赖树，`uv pip list` 看当前环境里已安装的包和版本。声明写在 `pyproject.toml`，实际锁定版本看 `uv.lock`。

加包、删包：

```powershell
uv add 包名
uv remove 包名
```
