"""文本切分模块 — 使用 LangChain RecursiveCharacterTextSplitter"""

from langchain_text_splitters import RecursiveCharacterTextSplitter


_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
    separators=["\n\n", "\n", "。", "；", "，", " ", ""],
)


def split_text(text: str) -> list[str]:
    """切分文本，返回 chunk 列表"""
    return _splitter.split_text(text)
