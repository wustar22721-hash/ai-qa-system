"""文档加载模块 — 递归读取本地 Markdown 文件"""

from pathlib import Path


def load_markdown_files(folder: str | Path) -> list[dict[str, str]]:
    """递归读取指定文件夹下所有 .md 文件，返回 [{"path": ..., "content": ...}, ...]"""
    folder = Path(folder)
    if not folder.is_dir():
        raise NotADirectoryError(f"路径不存在或不是文件夹: {folder}")

    results: list[dict[str, str]] = []
    for md_file in sorted(folder.rglob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        results.append({"path": str(md_file.resolve()), "content": content})

    return results
