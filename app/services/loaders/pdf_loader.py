"""PDF 文件 loader — 使用 PyMuPDF (fitz)，每页一个 Document"""

import re
from pathlib import Path

import fitz
from langchain_core.documents import Document

from app.services.loaders.base import BaseLoader, make_document_id


def _clean_pdf_text(text: str) -> str:
    """清洗 PDF 提取文本：去多余空行、页码噪声、trim"""
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # 跳过纯页码行
        if stripped.isdigit() and len(stripped) <= 4:
            continue
        cleaned.append(stripped)

    text = "\n".join(cleaned)
    # 折叠连续空行（3+ → 2）
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class PdfLoader(BaseLoader):
    """使用 PyMuPDF 加载 PDF，每页生成一个 LangChain Document。"""

    file_extensions = [".pdf"]

    @staticmethod
    def load(file_path: Path, *, base_dir: Path) -> list[Document]:
        docs: list[Document] = []

        rel_path = file_path.resolve().relative_to(base_dir.resolve())
        rel_path_str = str(rel_path).replace("\\", "/")

        # category: PDF 根目录下的子目录名，如果 PDF 直接在 pdf/ 下则为 "pdf"
        parts = rel_path.parts
        if len(parts) >= 3:
            category = parts[1]
        else:
            category = "pdf"

        document_id = make_document_id(rel_path_str)

        try:
            pdf_doc = fitz.open(str(file_path))
        except Exception:
            return docs

        for page_num in range(pdf_doc.page_count):
            page = pdf_doc[page_num]
            text = page.get_text()
            if not text or not text.strip():
                continue

            text = _clean_pdf_text(text)
            if len(text) < 20:  # 跳过内容过少的页
                continue

            docs.append(Document(
                page_content=text,
                metadata={
                    "document_id": document_id,
                    "source": file_path.name,
                    "file_path": rel_path_str,
                    "file_type": "pdf",
                    "category": category,
                    "page": page_num + 1,  # 页码从 1 开始
                },
            ))

        pdf_doc.close()
        return docs
