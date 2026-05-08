"""Document loader 抽象基类 — 定义统一的 Document 结构与 loader 接口"""

import hashlib
from abc import ABC, abstractmethod
from pathlib import Path

from langchain_core.documents import Document

# ── metadata 字段约定 ──────────────────────────────────────
# 所有 loader 产出的 Document.metadata 必须包含以下字段：
#
#   document_id   基于知识库内相对路径生成的唯一 ID（去重、增量更新用）
#   source        文件名（如 "如何创建群组.md"），UI 展示和来源标注用
#   file_path     相对于知识库根目录的完整路径（如 "md/视频会议/xxx.md"）
#   file_type     文件扩展名（小写，不含点号）："md" | "pdf" | "xlsx"
#   category      分类名：md 文件为其所在的子目录名，其他格式为直属目录名或 "未分类"
#
# chunk_id 在后续 split 阶段生成，格式为 "{document_id}#chunk{N}"，
# 用于来源追溯（source trace）和 rerank 时的 chunk 级别定位。
# ─────────────────────────────────────────────────────────────


def make_document_id(file_path: str) -> str:
    """基于文件在知识库内的相对路径，生成稳定的唯一 ID。

    使用路径字符串的 SHA256 前 12 位，比完整路径更短，但仍保证唯一性。
    """
    digest = hashlib.sha256(file_path.encode("utf-8")).hexdigest()
    return digest[:12]


class BaseLoader(ABC):
    """所有格式 loader 的抽象基类。

    子类需实现 load()，返回 LangChain Document 列表。
    """

    # 子类覆盖此字段声明自己处理的文件扩展名（小写，含点号）
    file_extensions: list[str] = []

    @staticmethod
    @abstractmethod
    def load(file_path: Path, *, base_dir: Path) -> list[Document]:
        """从单个文件加载为 Document 列表。

        Args:
            file_path: 文件的绝对路径
            base_dir: 知识库根目录的绝对路径（用于计算相对路径、分类）

        Returns:
            LangChain Document 列表。单个文件可能产出多个 Document
            （例如 PDF 按页拆分），但大多数格式返回单元素列表。
        """
        ...
