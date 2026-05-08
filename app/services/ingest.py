"""Ingest 流水线编排 — 加载 → 清洗 → 切分 → 过滤 → 入库

全流程统一使用 LangChain Document，不中途退化为 dict。
"""

import logging

from app.services.cleaner import clean_documents
from app.services.embedding import get_embeddings
from app.services.loader_manager import load_all_documents
from app.services.splitter import split_documents
from app.services.vectorstore import build_vector_store, filter_for_index

logger = logging.getLogger(__name__)

# ── 阶段标签前缀 ─────────────────────────────────────────────
_PFX = "[INGEST]"


def run_ingest(base_dir: str) -> int:
    """执行全量 ingest 流水线，返回最终入库 chunk 数。

    流水线阶段：
        1. load_all_documents()  → 递归扫描 + 分派 loader
        2. clean_documents()     → Markdown 清洗（md 类型）
        3. split_documents()     → 文本切分 + chunk_id 生成
        4. filter_for_index()    → 质量过滤
        5. build_vector_store()  → embedding + 写入 Chroma
    """
    # ── 阶段 1: 加载 ─────────────────────────────────────────
    logger.info("%s 开始加载文档...", _PFX)
    docs = load_all_documents(base_dir)
    logger.info("%s 加载完成: %d 个 Document", _PFX, len(docs))

    # ── 阶段 2: 清洗 ─────────────────────────────────────────
    logger.info("%s 开始清洗...", _PFX)
    docs = clean_documents(docs)
    logger.info("%s 清洗完成: %d 个 Document", _PFX, len(docs))

    # ── 阶段 3: 切分 ─────────────────────────────────────────
    logger.info("%s 开始切分...", _PFX)
    chunks = split_documents(docs)
    logger.info("%s 切分完成: %d → %d 个 chunk", _PFX, len(docs), len(chunks))

    # ── 阶段 4: 过滤 ─────────────────────────────────────────
    logger.info("%s 开始过滤...", _PFX)
    before = len(chunks)
    chunks = filter_for_index(chunks)
    after = len(chunks)
    logger.info("%s 过滤完成: %d → %d (剔除 %d)", _PFX, before, after, before - after)

    # ── 阶段 5: 向量化 & 入库 ───────────────────────────────
    logger.info("%s 开始向量化...", _PFX)
    get_embeddings()  # 预热 embedding 模型（首次会下载）
    build_vector_store(chunks)
    logger.info("%s 入库完成: %d 条 chunk 已写入 Chroma", _PFX, after)

    return after
