"""Rerank 模块 — 排序 + 定义类 chunk 加权"""

_STOP_CHARS = set("的了吗呢啊吧是有在哪个哪些怎么如何什么这那一二三")

# 控制能力关键词（权限定义的核心标志）
_CONTROL_KEYWORDS = [
    "设置", "管理", "控制", "允许", "禁止",
    "权限", "入会权限", "发言权限", "共享权限", "静音",
]

# 一般定义关键词（辅助）
_DEFINITION_KEYWORDS = [
    "包括", "包含", "分为", "是指", "定义",
    "功能", "作用", "能力", "支持", "可以",
    "用于", "提供",
]


def _keyword_overlap(query: str, content: str) -> float:
    """query 中双字词在 chunk 中的命中比例"""
    chars = [ch for ch in query if ch not in _STOP_CHARS and ch.strip()]
    if len(chars) < 2:
        if not chars:
            return 0.0
        return sum(1 for ch in chars if ch in content) / len(chars)

    bigrams = [chars[i] + chars[i + 1] for i in range(len(chars) - 1)]
    if not bigrams:
        return 0.0
    hits = sum(1 for bg in bigrams if bg in content)
    return hits / len(bigrams)


def _permission_boost(content: str) -> float:
    """权限查询专用：控制能力关键词高权重 + 一般定义关键词低权重"""
    control_hits = sum(1 for kw in _CONTROL_KEYWORDS if kw in content)
    def_hits = sum(1 for kw in _DEFINITION_KEYWORDS if kw in content)
    return min(0.04 * control_hits + 0.02 * def_hits, 0.15)


def _is_permission_query(query: str) -> bool:
    """判断 query 是否在询问权限/功能类问题"""
    return any(kw in query for kw in ["权限", "功能"])


def _extract_source(d: dict[str, object]) -> str:
    """从旧格式 (d['source']) 或新格式 (d['metadata']['source']) 提取 source"""
    if "metadata" in d and isinstance(d["metadata"], dict):
        return str(d["metadata"].get("source", ""))
    return str(d.get("source", ""))


def rerank(
    query: str,
    docs: list[dict[str, object]],
    top_k: int = 5,
    keyword_weight: float = 0.3,
) -> list[dict[str, object]]:
    """对检索结果重排序：向量距离 + 关键词重叠 + 定义加权，取 top_k。

    接受两种输入格式：
      旧: [{content, source, score}]
      新: [{content, score, metadata: {source, chunk_id, category, ...}}]
    输出始终透传 metadata（如果输入中有）。
    """

    if not docs:
        return []

    is_perm = _is_permission_query(query)
    scored: list[tuple[float, dict[str, object]]] = []

    for d in docs:
        content = str(d["content"])
        source = _extract_source(d)
        chroma_score = float(d.get("score", 1.0))

        vec_sim = 1.0 / (1.0 + chroma_score)
        keyword_sim = _keyword_overlap(query, content)
        combined = (1 - keyword_weight) * vec_sim + keyword_weight * keyword_sim

        # 权限/功能类 query：控制能力关键词加权
        if is_perm:
            combined += _permission_boost(content)

        out: dict[str, object] = {"content": content, "source": source}
        # 透传 metadata（如果输入中有）
        if "metadata" in d:
            out["metadata"] = d["metadata"]

        scored.append((combined, out))

    scored.sort(key=lambda x: x[0], reverse=True)

    # 确保至少 1 个控制能力类 chunk 进入结果（兜底替换末位）
    if is_perm:
        ctrl_idx = next(
            (i for i, (_, ch) in enumerate(scored)
             if _permission_boost(str(ch["content"])) > 0),
            None,
        )
        if ctrl_idx is not None and ctrl_idx >= top_k:
            scored[top_k - 1] = scored[ctrl_idx]

    return [item for _, item in scored[:top_k]]
