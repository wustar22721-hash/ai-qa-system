"""Excel 文件 loader — 使用 pandas + openpyxl，每个 sheet 一个 Document"""

from pathlib import Path

import pandas as pd
from langchain_core.documents import Document

from app.services.loaders.base import BaseLoader, make_document_id


def _sheet_to_text(df: pd.DataFrame, sheet_name: str) -> str:
    """将 DataFrame 转为自然语言文本，每行一段，跳过 NaN 值"""
    lines = [f"【Sheet: {sheet_name}】", ""]
    for _, row in df.iterrows():
        row_parts = []
        for col in df.columns:
            val = row[col]
            if pd.isna(val):
                continue
            row_parts.append(f"{col}: {val}")
        if row_parts:
            lines.append("\n".join(row_parts))
            lines.append("")
    return "\n".join(lines).strip()


class ExcelLoader(BaseLoader):
    """使用 pandas 加载 Excel，每个 sheet 生成一个 LangChain Document。"""

    file_extensions = [".xlsx"]

    @staticmethod
    def load(file_path: Path, *, base_dir: Path) -> list[Document]:
        docs: list[Document] = []

        rel_path = file_path.resolve().relative_to(base_dir.resolve())
        rel_path_str = str(rel_path).replace("\\", "/")

        parts = rel_path.parts
        if len(parts) >= 3:
            category = parts[1]
        else:
            category = "excel"

        document_id = make_document_id(rel_path_str)

        try:
            xls = pd.ExcelFile(str(file_path), engine="openpyxl")
        except Exception:
            return docs

        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name)
            if df.empty:
                continue

            text = _sheet_to_text(df, sheet_name)
            if not text or len(text.strip()) < 20:
                continue

            docs.append(Document(
                page_content=text,
                metadata={
                    "document_id": document_id,
                    "source": file_path.name,
                    "file_path": rel_path_str,
                    "file_type": "xlsx",
                    "category": category,
                    "sheet_name": sheet_name,
                },
            ))

        xls.close()
        return docs
