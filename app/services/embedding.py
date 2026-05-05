"""Embedding 模块 — 使用 HuggingFace BGE 中文模型"""

from langchain_huggingface import HuggingFaceEmbeddings


_embedding = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-zh",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)


def get_embeddings() -> HuggingFaceEmbeddings:
    """返回 HuggingFaceEmbeddings 实例（单例）"""
    return _embedding
