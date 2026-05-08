"""Markdown 清洗模块 — 去除图片、链接URL、视频文本、噪声行、多余空行"""

import re

# ── 正则（模块级编译）─────────────────────────────────────
_IMG_PATTERN = re.compile(r"!\[.*?\]\(.*?\)")
_LINK_PATTERN = re.compile(r"\[([^\]]*?)\]\(.*?\)")
_TIMESTAMP_PATTERN = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")

# 图片尺寸标记: 250px|700px|reset
_IMG_SIZE_PATTERN = re.compile(r"\d+px\s*\|\s*\d+px\s*\|\s*reset", re.IGNORECASE)

# 零宽字符
_ZERO_WIDTH_PATTERN = re.compile(r"[​‌‍‎‏﻿]")

# 表格分隔行: |---|:---:|---| 等
_TABLE_SEP_PATTERN = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$")

# 无意义行（仅含符号/标点/空白，长度 ≤ 5）
_PURE_SYMBOL_PATTERN = re.compile(
    r"^[\s\|\-—–·•●◎○□■△▲▽▼☆★♦♥♣♠✓✗☐☑☒⬜✅❌🔖📌📎📝�]{1,5}$"
)

_MULTI_BLANK_PATTERN = re.compile(r"\n{3,}")

# 视频关键词
_VIDEO_KEYWORDS = [
    "播放", "倍速", "快进", "快退", "暂停",
    "静音", "画中画", "全屏", "小窗",
]
_VIDEO_LINE_PATTERN = re.compile(
    r"^.*?(" + "|".join(map(re.escape, _VIDEO_KEYWORDS)) + r").*?$",
    re.IGNORECASE,
)
_VIDEO_INLINE_PATTERN = re.compile(
    r"\b(" + "|".join(map(re.escape, _VIDEO_KEYWORDS)) + r")\b",
    re.IGNORECASE,
)


def clean_markdown(text: str) -> str:
    """清洗 Markdown，返回干净字符串"""
    # 1. 删除图片 ![](url)
    text = _IMG_PATTERN.sub("", text)

    # 2. 链接 [text](url) → 保留文字
    text = _LINK_PATTERN.sub(r"\1", text)

    # 3. 删除图片尺寸标记 & 零宽字符 & 时间戳
    text = _IMG_SIZE_PATTERN.sub("", text)
    text = _ZERO_WIDTH_PATTERN.sub("", text)
    text = _TIMESTAMP_PATTERN.sub("", text)

    # 4. 逐行清理
    lines = text.split("\n")
    clean_lines: list[str] = []
    for line in lines:
        stripped = line.strip()

        # 跳过纯符号/无意义行
        if not stripped:
            clean_lines.append("")
            continue
        if _PURE_SYMBOL_PATTERN.match(stripped):
            continue
        if _TABLE_SEP_PATTERN.match(stripped):
            continue

        # 视频关键词行：去掉关键词后无实质内容则跳过
        if _VIDEO_LINE_PATTERN.match(stripped):
            remaining = _VIDEO_INLINE_PATTERN.sub("", stripped).strip()
            if len(remaining) <= 3:
                continue

        # 行内删除残余视频关键词
        line = _VIDEO_INLINE_PATTERN.sub("", line)
        clean_lines.append(line)

    # 5. 折叠多余空行：≥3 → 2
    text = _MULTI_BLANK_PATTERN.sub("\n\n", "\n".join(clean_lines))

    return text.strip()


def clean_documents(docs):
    """对 Document 列表逐条清洗 page_content，保留 metadata。

    目前仅清洗 file_type == "md" 的文档，其他格式直接透传。
    """
    for doc in docs:
        if doc.metadata.get("file_type") == "md":
            doc.page_content = clean_markdown(doc.page_content)
    return docs
