"""
应用配置 —— 基于 Pydantic Settings 的参数校验和管理
"""
import os
from pathlib import Path

# 确保加载项目根目录的 .env（python-dotenv 为可选依赖，缺失时直接读环境变量）
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass


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
MYSQL_HOST = _optional("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(_optional("MYSQL_PORT", "3306"))
MYSQL_USER = _optional("MYSQL_USER", "root")
MYSQL_PASSWORD = _optional("MYSQL_PASSWORD", "")
MYSQL_DB = _optional("MYSQL_DB", "smart_campus")

# ============================================================
# LLM 配置
# ============================================================
ZHIPUAI_API_KEY = _require("ZHIPUAI_API_KEY")

# ============================================================
# 邮箱配置
# ============================================================
EMAIL_USER = _optional("EMAIL_USER", "")
EMAIL_PASSWORD = _optional("EMAIL_PASSWORD", "")

# ============================================================
# Agent 配置
# ============================================================
AGENT_MAX_REFLECTION = int(_optional("AGENT_MAX_REFLECTION", "2"))
AGENT_MODEL = _optional("AGENT_MODEL", "glm-4-plus")
AGENT_TEMPERATURE = float(_optional("AGENT_TEMPERATURE", "0.1"))
AGENT_TIMEOUT = int(_optional("AGENT_TIMEOUT", "120"))

# ============================================================
# RAG 配置
# ============================================================
RAG_EMBEDDING_MODEL = _optional("RAG_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
RAG_VECTORSTORE_PATH = _optional("RAG_VECTORSTORE_PATH", "rag/vectorstore")
RAG_RETRIEVAL_K = int(_optional("RAG_RETRIEVAL_K", "5"))
RAG_CHUNK_SIZE = int(_optional("RAG_CHUNK_SIZE", "200"))
RAG_CHUNK_OVERLAP = int(_optional("RAG_CHUNK_OVERLAP", "20"))

# ============================================================
# 应用配置
# ============================================================
APP_HOST = _optional("APP_HOST", "127.0.0.1")
APP_PORT = int(_optional("APP_PORT", "7860"))
DEBUG_MODE = _optional("DEBUG_MODE", "false").lower() == "true"
