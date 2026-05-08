"""文本切分模块 — 使用 LangChain RecursiveCharacterTextSplitter"""

from langchain_text_splitters import RecursiveCharacterTextSplitter

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
    separators=["\n\n", "\n", "。", "；", "，", " ", ""],
)


def split_text(text: str) -> list[str]:
    """切分文本，返回 chunk 字符串列表（保留兼容旧调用方）"""
    return _splitter.split_text(text)


def split_documents(docs):
    """切分 Document 列表，保留原始 metadata，新增 chunk_id 和 chunk_index。

    chunk_index 是文档内索引（每个文档从 0 开始）。
    chunk_id 格式: "{document_id}_{chunk_index}"
    """
    all_chunks = []
    for doc in docs:
        sub_chunks = _splitter.split_documents([doc])
        doc_id = doc.metadata.get("document_id", "unknown")
        for i, ch in enumerate(sub_chunks):
            ch.metadata["chunk_id"] = f"{doc_id}_{i}"
            ch.metadata["chunk_index"] = i
        all_chunks.extend(sub_chunks)
    return all_chunks
