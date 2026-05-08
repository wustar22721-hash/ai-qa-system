"""全局配置 — 从环境变量读取"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# DeepSeek
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-v4-pro")
# Query Rewriting 使用轻量非推理模型，避免 reasoning_content 空 content 问题
REWRITER_MODEL = os.getenv("REWRITER_MODEL", "deepseek-chat")

# Chroma
CHROMA_PERSIST_DIR = str(BASE_DIR / os.getenv("CHROMA_PERSIST_DIR", "data/chroma"))

# 知识库（多格式：md/pdf/xlsx）
KNOWLEDGE_DIR = str(BASE_DIR / "飞书FAQ_知识库")
