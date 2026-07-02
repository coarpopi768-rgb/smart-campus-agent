"""
应用配置 —— 基于 Pydantic Settings 的参数校验和管理
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 确保加载项目根目录的 .env
load_dotenv(Path(__file__).parent.parent / ".env")


class ConfigError(Exception):
    """配置错误异常"""
    pass


def _require(key: str) -> str:
    """读取必需的环境变量，不存在则抛出异常"""
    value = os.getenv(key)
    if not value:
        raise ConfigError(f"缺少必需的环境变量: {key}，请在 .env 文件中配置")
    return value


def _optional(key: str, default: str = "") -> str:
    """读取可选的环境变量"""
    return os.getenv(key, default)


# ============================================================
# 数据库配置
# ============================================================
MYSQL_HOST = _optional("mysql_host", "127.0.0.1")
MYSQL_PORT = int(_optional("mysql_port", "3306"))
MYSQL_USER = _optional("mysql_user", "root")
MYSQL_PASSWORD = _optional("mysql_password", "")
MYSQL_DB = _optional("mysql_db", "smart_campus")

# ============================================================
# LLM 配置
# ============================================================
ZHIPUAI_API_KEY = _require("zhipuai_api_key")

# ============================================================
# 邮箱配置
# ============================================================
EMAIL_USER = _optional("email_user", "")
EMAIL_PASSWORD = _optional("email_password", "")

# ============================================================
# Agent 配置
# ============================================================
AGENT_MAX_REFLECTION = int(_optional("agent_max_reflection", "2"))
AGENT_MODEL = _optional("agent_model", "glm-4-plus")
AGENT_TEMPERATURE = float(_optional("agent_temperature", "0.1"))
AGENT_TIMEOUT = int(_optional("agent_timeout", "120"))

# ============================================================
# RAG 配置
# ============================================================
RAG_EMBEDDING_MODEL = _optional("rag_embedding_model", "all-MiniLM-L6-v2")
RAG_VECTORSTORE_PATH = _optional("rag_vectorstore_path", "rag/vectorstore")
RAG_RETRIEVAL_K = int(_optional("rag_retrieval_k", "5"))
RAG_CHUNK_SIZE = int(_optional("rag_chunk_size", "200"))
RAG_CHUNK_OVERLAP = int(_optional("rag_chunk_overlap", "20"))

# ============================================================
# 应用配置
# ============================================================
APP_HOST = _optional("app_host", "127.0.0.1")
APP_PORT = int(_optional("app_port", "7860"))
DEBUG_MODE = _optional("debug_mode", "false").lower() == "true"
