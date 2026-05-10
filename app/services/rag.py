"""RAG 问答模块 — Query Rewriting → 检索 → Rerank → 拼接上下文 → LLM 生成答案"""

import logging

from app.services.llm import generate_answer
from app.services.reranker import rerank
from app.services.rewriter import rewrite_query
from app.services.vectorstore import similarity_search_with_metadata

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """你是一个基于飞书帮助文档的问答助手。请严格根据以下上下文回答问题。

通用规则：
1. 只能根据上下文作答，绝对不能胡编、猜测或使用外部知识
2. 仔细阅读全部上下文，综合多个 chunk 的信息，给出尽可能完整的回答
3. 每一条结论都必须能在上下文中找到依据，并在该条末尾标注"（来源：文件名.md）"
4. 可以用自己的语言组织表达，但不允许添加上下文未提供的信息
5. 优先以要点形式列出，确保不遗漏任何重要内容
6. 如果上下文信息不完整，说明"根据现有资料，该信息暂未收录"
7. 如果上下文中没有明确答案，回答"未在知识库中找到相关信息"
8. 不允许根据常识推测，即使你知道答案也不能说

权限/功能类问题补充规则：
9. 权限 = 该角色对他人或会议的控制能力，核心标志词为"设置""管理""控制""允许""禁止"
10. 不属于权限的内容，即使上下文出现也必须排除：
    - 角色变更：转交主持人、成为主持人、收回主持人、指定主持人
    - 流程操作：结束会议、离开会议、发起会议、入会
    - 操作步骤：点击xxx按钮、在xxx页面中选择
11. 允许跨 chunk 拼接完整列表，优先引用含"设置""管理""控制"的原文

回答格式（权限/功能类问题）：
12. 合并去重：语义相近的权限合并为一条，取最完整的表述。如"设置入会范围"和"修改入会权限"合并为"设置入会权限"
13. 避免同一条权限用不同措辞重复出现
14. 按以下结构输出：
    核心权限：
    - 每类控制能力只列一条，不重复
    补充权限（可选）：
    - 如果存在不属于核心控制、但明确是权限定义的内容，在此列出
    - 与核心权限无重叠，没有则省略此节"""


def _build_prompt(query: str, contexts: list[dict[str, str]]) -> str:
    parts = [SYSTEM_INSTRUCTION, "", "【参考上下文】"]
    for i, ctx in enumerate(contexts, 1):
        fname = ctx.get("source", "未知文件")
        parts.append(f"[来源：{fname}]\n{ctx['content']}")
    parts.append(f"【用户问题】\n{query}")
    return "\n\n".join(parts)


def _merge_sources(
    contexts: list[dict[str, object]], max_content_len: int = 400
) -> list[dict[str, object]]:
    """按文件名去重合并 chunk，收集 chunk_ids，控制每个文件的内容长度"""
    merged: dict[str, str] = {}
    chunk_ids: dict[str, list[str]] = {}  # file → [chunk_id, ...]
    seen: list[str] = []

    for ctx in contexts:
        fname = ctx.get("source", "")
        chunk_content = ctx.get("content", "")
        if fname not in merged:
            seen.append(fname)
            merged[fname] = chunk_content
            chunk_ids[fname] = []
        else:
            remaining = max_content_len - len(merged[fname])
            if remaining > 0 and chunk_content.strip():
                merged[fname] += "\n...\n" + chunk_content[:remaining]

        # 收集 chunk_id
        meta = ctx.get("metadata", {})
        if isinstance(meta, dict) and meta.get("chunk_id"):
            chunk_ids[fname].append(meta["chunk_id"])

    return [
        {
            "file": f,
            "content": merged[f][:max_content_len],
            "chunk_ids": chunk_ids.get(f, []),
        }
        for f in seen
    ]


def rag_chat(query: str, history: list[dict[str, str]] | None = None, top_k: int = 5) -> dict:
    """RAG 问答：Query Rewriting → 检索 top10 → Rerank → 取 top5 → LLM 生成"""
    # 0. Query Rewriting：将口语化/不完整的 query 改写为独立检索语句
    search_query = rewrite_query(query, history=history)

    # 1. 检索 top_k * 2 条（带完整 metadata），使用改写后的 search_query
    candidates = similarity_search_with_metadata(search_query, top_k=top_k * 2)

    # 2. Rerank：向量距离 + 关键词重叠 综合排序 → 取 top_k
    contexts = rerank(search_query, candidates, top_k=top_k)

    # 3. 构造 prompt
    prompt = _build_prompt(query, contexts)

    # 4. 调用 LLM
    answer = generate_answer(prompt)

    # 5. 按文件名去重合并来源
    sources = _merge_sources(contexts)

    return {
        "query": query,
        "answer": answer,
        "sources": sources,
    }
