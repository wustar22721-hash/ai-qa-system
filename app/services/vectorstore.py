"""向量数据库模块 — Chroma 持久化与检索"""

from langchain_chroma import Chroma

from app.core.config import CHROMA_PERSIST_DIR
from app.services.embedding import get_embeddings

_vectorstore: Chroma | None = None


def _count_meaningful(text: str) -> int:
    """统计有意义的字符数（中英文+数字，排除标点和空白）"""
    count = 0
    for ch in text:
        if ch.isspace():
            continue
        # 中文、英文、数字
        if "一" <= ch <= "鿿" or ch.isascii() and (ch.isalnum()):
            count += 1
    return count


def _is_table_chunk(content: str, threshold: float = 0.3) -> bool:
    """判断是否为表格/对比类 chunk：含 | 的行占比超过阈值"""
    lines = [ln for ln in content.split("\n") if ln.strip()]
    if len(lines) < 2:
        return False
    pipe_lines = sum(1 for ln in lines if "|" in ln)
    return pipe_lines / len(lines) >= threshold


def filter_for_index(chunks, min_chars: int = 30):
    """入库前过滤：剔除表格/对比类、过短、无语义的 chunk。接受 list[Document]"""

    from langchain_core.documents import Document

    kept: list[Document] = []
    removed_table = 0
    removed_short = 0

    for ch in chunks:
        content = ch.page_content if isinstance(ch, Document) else ch.get("content", "")

        # 过短或无语义
        if _count_meaningful(content) < min_chars:
            removed_short += 1
            continue

        # 表格/对比类
        if _is_table_chunk(content):
            removed_table += 1
            continue

        kept.append(ch)

    if removed_table or removed_short:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            "入库前过滤：剔除表格 %d 条、过短 %d 条，保留 %d 条",
            removed_table, removed_short, len(kept),
        )
    return kept


def build_vector_store(chunks) -> Chroma:
    """将 Document 列表写入 Chroma，所有 metadata 字段持久化存储"""
    global _vectorstore

    from langchain_core.documents import Document

    texts = [c.page_content for c in chunks]
    metadatas = [c.metadata for c in chunks]

    _vectorstore = Chroma.from_texts(
        texts=texts,
        embedding=get_embeddings(),
        metadatas=metadatas,
        persist_directory=CHROMA_PERSIST_DIR,
    )
    return _vectorstore


def load_vector_store() -> Chroma:
    """从磁盘加载已有向量库"""
    global _vectorstore
    _vectorstore = Chroma(
        embedding_function=get_embeddings(),
        persist_directory=CHROMA_PERSIST_DIR,
    )
    return _vectorstore


def similarity_search(query: str, top_k: int = 5) -> list[dict[str, str]]:
    """检索最相似的 top_k 个 chunk，返回 [{content, source}]"""
    if _vectorstore is None:
        raise RuntimeError("向量库未初始化，请先调用 build_vector_store() 或 load_vector_store()")
    docs = _vectorstore.similarity_search(query, k=top_k)
    return [
        {"content": d.page_content, "source": d.metadata.get("source", "")}
        for d in docs
    ]


def similarity_search_with_score(
    query: str, top_k: int = 10
) -> list[dict[str, object]]:
    """检索并返回相似度分数，返回 [{content, source, score}]。score 越低越相似。

    保留向后兼容。新代码请使用 similarity_search_with_metadata()。
    """
    if _vectorstore is None:
        raise RuntimeError("向量库未初始化，请先调用 build_vector_store() 或 load_vector_store()")
    docs_and_scores = _vectorstore.similarity_search_with_score(query, k=top_k)
    return [
        {
            "content": doc.page_content,
            "source": doc.metadata.get("source", ""),
            "score": score,
        }
        for doc, score in docs_and_scores
    ]


def similarity_search_with_metadata(
    query: str, top_k: int = 10
) -> list[dict[str, object]]:
    """检索并返回完整 metadata，返回 [{content, score, metadata}]。

    metadata 字段: document_id, chunk_id, chunk_index, source,
                   file_path, file_type, category
    """
    if _vectorstore is None:
        raise RuntimeError("向量库未初始化，请先调用 build_vector_store() 或 load_vector_store()")
    docs_and_scores = _vectorstore.similarity_search_with_score(query, k=top_k)
    return [
        {
            "content": doc.page_content,
            "score": score,
            "metadata": dict(doc.metadata),
        }
        for doc, score in docs_and_scores
    ]
