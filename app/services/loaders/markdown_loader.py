"""Markdown 文件 loader — 单个 .md 文件 → list[Document]"""

from pathlib import Path

from langchain_core.documents import Document

from app.services.loaders.base import BaseLoader, make_document_id


class MarkdownLoader(BaseLoader):
    """加载单个 .md 文件为一个 LangChain Document。"""

    file_extensions = [".md"]

    @staticmethod
    def load(file_path: Path, *, base_dir: Path) -> list[Document]:
        content = file_path.read_text(encoding="utf-8")

        # 相对路径（用于 document_id 和 file_path metadata）
        rel_path = file_path.resolve().relative_to(base_dir.resolve())
        rel_path_str = str(rel_path).replace("\\", "/")

        # category = md 下的一级子目录名
        # 路径格式: md/视频会议/xxx.md → parts = ("md", "视频会议", "xxx.md")
        parts = rel_path.parts
        if len(parts) >= 3:
            category = parts[1]       # 跳过格式目录 "md"
        else:
            category = "未分类"        # 文件直接在 md/ 下，无子分类

        metadata = {
            "document_id": make_document_id(rel_path_str),
            "source": file_path.name,
            "file_path": rel_path_str,
            "file_type": "md",
            "category": category,
        }

        return [Document(page_content=content, metadata=metadata)]
