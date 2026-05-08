"""统一文档加载调度器 — 递归扫描 + 扩展名分派 + 聚合 LangChain Document[]"""

import logging
from pathlib import Path

from langchain_core.documents import Document

from app.services.loaders.base import BaseLoader
from app.services.loaders.markdown_loader import MarkdownLoader
from app.services.loaders.pdf_loader import PdfLoader
from app.services.loaders.excel_loader import ExcelLoader

logger = logging.getLogger(__name__)

# ── Loader 注册表 ────────────────────────────────────────────
# 扩展名（小写，含点号） → BaseLoader 子类
# 新增格式只需在此注册，无需改动扫描逻辑。
# ──────────────────────────────────────────────────────────────

_LOADER_REGISTRY: dict[str, type[BaseLoader]] = {
    ".md": MarkdownLoader,
    ".pdf": PdfLoader,
    ".xlsx": ExcelLoader,
}


def _rel_path(file_path: Path, base_dir: Path) -> str:
    """返回 file_path 相对于 base_dir 的路径字符串（统一用 / 分隔）"""
    try:
        rel = file_path.resolve().relative_to(base_dir.resolve())
    except ValueError:
        # 文件不在 base_dir 下时回退到绝对路径
        rel = file_path.resolve()
    return str(rel).replace("\\", "/")


def load_all_documents(base_dir: str | Path) -> list[Document]:
    """递归扫描 base_dir，按扩展名分派 loader，聚合所有 Document。

    Args:
        base_dir: 知识库根目录路径

    Returns:
        所有成功加载的 LangChain Document 列表。
        每个 Document.metadata 包含 document_id, source, file_path,
        file_type, category 五个字段。
    """
    base_dir = Path(base_dir).resolve()
    if not base_dir.is_dir():
        raise NotADirectoryError(f"知识库目录不存在: {base_dir}")

    # 收集所有可处理的文件（按 registry 中注册的扩展名过滤）
    all_files: list[Path] = []
    skipped_extensions: set[str] = set()

    for f in sorted(base_dir.rglob("*")):
        if not f.is_file():
            continue
        ext = f.suffix.lower()
        if ext in _LOADER_REGISTRY:
            all_files.append(f)
        else:
            skipped_extensions.add(ext)

    if skipped_extensions:
        logger.info(
            "[SKIP] 未注册的扩展名: %s（这些文件将被跳过）",
            ", ".join(sorted(skipped_extensions)),
        )

    # 逐文件加载
    documents: list[Document] = []
    success = 0
    failed = 0
    skipped = 0

    for f in all_files:
        ext = f.suffix.lower()
        rel = _rel_path(f, base_dir)
        loader_cls = _LOADER_REGISTRY[ext]

        try:
            logger.info("[LOAD] %s", rel)
            docs = loader_cls.load(f, base_dir=base_dir)
            documents.extend(docs)
            success += 1
        except Exception:
            logger.exception("[ERROR] 加载失败: %s", rel)
            failed += 1

    # 汇总
    total_files = len(all_files) + len(skipped_extensions)  # 近似
    logger.info("=" * 60)
    logger.info(
        "加载完成: 扫描文件 %d, 成功 %d, 失败 %d, 跳过 %d（%d 种未注册扩展名）",
        len(all_files), success, failed,
        sum(1 for _ in base_dir.rglob("*") if _.is_file() and _.suffix.lower() not in _LOADER_REGISTRY),
        len(skipped_extensions),
    )
    logger.info("共生成 %d 个 LangChain Document", len(documents))

    return documents
