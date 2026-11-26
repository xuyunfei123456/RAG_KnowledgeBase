# 运行配置。密钥和引导账号只从环境变量读。
from pathlib import Path
from urllib.parse import unquote, urlparse

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# api/app/config.py → 仓库根。原文件和 LightRAG 缓存都相对这里。
REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    database_url: str = "postgresql+asyncpg://rag:rag@127.0.0.1:5432/rag"
    session_secret: str = "dev-session-secret-change-me"
    bootstrap_username: str = "admin"
    bootstrap_password: str = "admin123"
    cors_origin: str = "http://localhost:5173"

    # 生成模型：独立供应商（OpenAI 兼容）
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""

    # Embedding：另一家供应商（OpenAI 兼容），与生成模型分开写
    embedding_api_key: str = ""
    embedding_base_url: str = ""
    embedding_model: str = ""
    embedding_dim: int = 1024

    # 本机 MinerU api-server。不要把 mineru 包装进本仓库。
    mineru_api_url: str = "http://127.0.0.1:8001"
    mineru_tier: str = "flash"
    mineru_ocr_mode: str = "txt"

    @computed_field
    @property
    def postgres(self) -> dict[str, str]:
        raw = self.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        parsed = urlparse(raw)
        if not parsed.hostname or not parsed.path.lstrip("/"):
            raise RuntimeError("DATABASE_URL 必须是 postgresql://用户:密码@主机:端口/库名")
        return {
            "host": parsed.hostname,
            "port": str(parsed.port or 5432),
            "user": unquote(parsed.username or ""),
            "password": unquote(parsed.password or ""),
            "database": parsed.path.lstrip("/"),
        }

    @computed_field
    @property
    def llm_ready(self) -> bool:
        return bool(
            self.llm_api_key.strip()
            and self.llm_base_url.strip()
            and self.llm_model.strip()
        )

    @computed_field
    @property
    def embedding_ready(self) -> bool:
        return bool(
            self.embedding_api_key.strip()
            and self.embedding_base_url.strip()
            and self.embedding_model.strip()
        )

    @computed_field
    @property
    def models_ready(self) -> bool:
        return self.llm_ready and self.embedding_ready

    def missing_model_config(self) -> str | None:
        missing: list[str] = []
        if not self.llm_ready:
            missing.append("LLM_API_KEY / LLM_BASE_URL / LLM_MODEL")
        if not self.embedding_ready:
            missing.append("EMBEDDING_API_KEY / EMBEDDING_BASE_URL / EMBEDDING_MODEL")
        if not missing:
            return None
        return "未配置 " + "；以及 ".join(missing)


settings = Settings()
