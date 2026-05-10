"""RAG 问答模块 —— 检索增强生成的完整流水线

一句话概括：用户提问 → 改写问题 → 向量检索 → 重排序 → 拼接上下文 → LLM 生成答案

详细流程（5 步）：
    第 0 步 Query Rewriting（查询改写）
        用户在对话中可能说"那它的功能呢？"这种不完整的话，
        需要结合历史记录把它改写成一个独立、完整的检索语句，比如"飞书会议的功能有哪些？"
        这样向量检索才能找到正确的结果。

    第 1 步 向量检索（Vector Search）
        把改写后的查询转为向量（一组数字），在向量数据库中找"距离最近"的文档片段。
        距离越近 = 内容越相关。这一步取 top_k * 2 条候选项（冗余一些，交给下一步精排）。

    第 2 步 重排序（Rerank）
        向量相似度不是完美的，有些结果向量接近但内容不相关。
        重排序通过综合"向量距离分数"和"关键词重叠度"重新打分排序，
        最终只保留最相关的 top_k 条。

    第 3 步 构造 Prompt
        把检索到的文档片段和用户问题拼成一个完整的提示词，
        包含系统指令（告诉 LLM 回答规则）+ 参考上下文 + 用户问题。

    第 4 步 LLM 生成
        将构造好的 prompt 发送给大语言模型（LLM），由模型根据上下文生成最终答案。
"""

# ============================================================
# 导入依赖
# ============================================================

import logging

# 各子模块：每个文件负责 RAG 流水线中的一环
from app.services.llm import generate_answer, generate_answer_stream  # LLM 调用
from app.services.reranker import rerank                 # 对检索结果重排序（向量距离 + 关键词匹配）
from app.services.rewriter import rewrite_query          # 查询改写：补全不完整的问题
from app.services.vectorstore import similarity_search_with_metadata  # 向量相似度检索

logger = logging.getLogger(__name__)


# ============================================================
# 系统指令（System Prompt）
# ============================================================

# 系统指令是给 LLM 的"行为准则"，告诉它应该怎么回答问题。
# LLM 会作为"飞书帮助文档问答助手"的角色来遵循这些规则。
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


# ============================================================
# 辅助函数
# ============================================================

def _build_prompt(query: str, contexts: list[dict[str, str]]) -> str:
    """
    构造发送给 LLM 的完整 prompt。

    结构：
        1. 系统指令（告诉 LLM 回答规则）
        2. 参考上下文（从知识库检索到的相关文档片段）
        3. 用户问题

    参数：
        query:    用户原始问题（未经改写）
        contexts: 检索+重排序后的文档片段列表，每项包含 source（文件名）和 content（内容）

    返回值：
        拼接好的完整 prompt 字符串，可以直接发给 LLM

    示例输出结构：
        你是一个基于飞书帮助文档的问答助手。请严格根据以下上下文回答问题。
        ...（规则）...

        【参考上下文】
        [来源：权限说明.md]
        管理员可以设置入会权限...

        【用户问题】
        管理员有哪些权限？
    """
    # parts 列表用于存储 prompt 的各个部分，最后用两个换行符拼接
    parts = [SYSTEM_INSTRUCTION, "", "【参考上下文】"]

    # 遍历每条上下文，标注来源文件名
    for i, ctx in enumerate(contexts, 1):  # enumerate(..., 1) 从 1 开始计数（虽然这里没用到 i）
        fname = ctx.get("source", "未知文件")     # 取文件名，没有则显示"未知文件"
        parts.append(f"[来源：{fname}]\n{ctx['content']}")  # 格式：[来源：xxx.md]\n内容...

    # 最后加上用户问题
    parts.append(f"【用户问题】\n{query}")
    return "\n\n".join(parts)  # 各部分之间用两个换行分隔，方便 LLM 区分结构


def _merge_sources(
    contexts: list[dict[str, object]], max_content_len: int = 400
) -> list[dict[str, object]]:
    """
    按文件名去重合并 chunk（文档片段），控制每个来源文件的内容长度。

    为什么要合并？
        检索可能返回同一个文件的多个片段（chunk），比如"权限说明.md"的第 3 段和第 7 段。
        如果直接返回给前端，会出现"权限说明.md"出现多次的情况，阅读体验不好。
        所以按文件名合并，每个文件只保留一条记录，但要限制内容长度防止太长。

    参数：
        contexts:        检索到的原始上下文列表（可能同一文件多个片段）
        max_content_len: 每个文件最多保留多少个字符（默认 400）

    返回值：
        去重合并后的来源列表，每项有 file（文件名）、content（合并后内容）、chunk_ids（片段 ID 列表）

    示例：
        输入: [
            {source: "a.md", content: "AAA", metadata: {chunk_id: "a-0"}},
            {source: "a.md", content: "BBB", metadata: {chunk_id: "a-1"}},
            {source: "b.md", content: "CCC", metadata: {chunk_id: "b-0"}},
        ]
        输出: [
            {file: "a.md", content: "AAA\n...\nBBB", chunk_ids: ["a-0", "a-1"]},
            {file: "b.md", content: "CCC", chunk_ids: ["b-0"]},
        ]
    """
    merged: dict[str, str] = {}           # 文件名 → 合并后的内容字符串
    chunk_ids: dict[str, list[str]] = {}  # 文件名 → 该文件中所有 chunk 的 ID 列表
    seen: list[str] = []                  # 记录文件名的出现顺序（保持返回列表的顺序稳定）

    for ctx in contexts:
        fname = ctx.get("source", "")        # 来源文件名
        chunk_content = ctx.get("content", "")  # 当前片段的内容

        # 该文件第一次出现：直接存储
        if fname not in merged:
            seen.append(fname)               # 记录顺序
            merged[fname] = chunk_content    # 存储内容
            chunk_ids[fname] = []            # 初始化 chunk ID 列表
        else:
            # 该文件已有内容：尝试追加（但不超过 max_content_len）
            remaining = max_content_len - len(merged[fname])  # 还能加多少字符
            if remaining > 0 and chunk_content.strip():       # 还有空间且内容非空
                merged[fname] += "\n...\n" + chunk_content[:remaining]  # 用 ... 分隔追加

        # 收集 chunk_id（用于前端定位高亮等）
        meta = ctx.get("metadata", {})
        if isinstance(meta, dict) and meta.get("chunk_id"):
            chunk_ids[fname].append(meta["chunk_id"])

    # 最终结果：按 seen 中的顺序构造返回列表，每个文件截断到 max_content_len
    return [
        {
            "file": f,
            "content": merged[f][:max_content_len],
            "chunk_ids": chunk_ids.get(f, []),
        }
        for f in seen
    ]


# ============================================================
# 核心函数：RAG 问答流水线
# ============================================================

def rag_chat(query: str, history: list[dict[str, str]] | None = None, top_k: int = 5) -> dict:
    """
    RAG 问答的完整流水线——这是整个模块的入口函数。

    执行流程（5 步）：
        第 0 步：Query Rewriting  → 把不完整/口语化的问题改写为独立检索语句
        第 1 步：向量检索         → 在知识库中找语义最相似 top_k*2 条文档片段
        第 2 步：Rerank 重排序    → 综合评分，从候选中精挑 top_k 条最相关的
        第 3 步：构造 Prompt      → 把文档片段 + 用户问题拼成发给 LLM 的提示词
        第 4 步：LLM 生成答案     → 调用大模型根据上下文生成最终回答
        第 5 步：合并来源         → 按文件名去重，整理引用来源

    参数：
        query:   用户输入的原始问题（如"管理员能做什么？"）
        history: 对话历史，每项为 {"role": "user/assistant", "content": "..."}
                 用于查询改写时理解上下文。比如用户刚问了"飞书会议"，
                 现在问"它的功能"→ 结合历史改写为"飞书会议的功能"
        top_k:   最终返回给 LLM 的文档片段数量（默认 5）
                 为什么检索时取 top_k*2？
                 因为向量检索不够精确，先多取一些候选项（10 条），
                 再通过重排序精挑出最相关的 5 条，提高最终答案质量。

    返回值（dict）：
        {
            "query":   "原始问题",
            "answer":  "LLM 生成的答案文本",
            "sources": [{file: "文件名", content: "引用内容", chunk_ids: [...]}, ...]
        }
    """
    # ---- 第 0 步：查询改写 ----
    # 例如用户问"那它的功能呢？"→ 结合历史改写为"飞书会议的功能有哪些？"
    search_query = rewrite_query(query, history=history)

    # ---- 第 1 步：向量相似度检索 ----
    # 在向量库中搜索与改写后查询最相似的 top_k*2=10 条文档片段
    # 每个片段都有 metadata（来源文件、chunk_id 等），用于后续合并和引用标注
    candidates = similarity_search_with_metadata(search_query, top_k=top_k * 2)

    # ---- 第 2 步：重排序精排 ----
    # 向量相似度不等于语义相关性（可能误召回），需要通过关键词等信号重新排序
    # 从 10 条候选中精挑最相关的 5 条（top_k）
    contexts = rerank(search_query, candidates, top_k=top_k)

    # ---- 第 3 步：构造 Prompt ----
    # 将系统指令 + 文档上下文 + 用户问题拼接成完整的 prompt
    prompt = _build_prompt(query, contexts)

    # ---- 第 4 步：调用 LLM 生成答案 ----
    # 把 prompt 发给大语言模型（如 GPT、DeepSeek 等），让它根据上下文生成回答
    answer = generate_answer(prompt)

    # ---- 第 5 步：整理引用来源 ----
    # 按文件名去重合并，控制每个文件的内容长度，方便前端展示
    sources = _merge_sources(contexts)

    # 返回完整结果
    return {
        "query": query,
        "answer": answer,
        "sources": sources,
    }


def rag_chat_stream(query: str, history: list[dict[str, str]] | None = None, top_k: int = 5):
    """RAG 流式问答生成器，用于 SSE 逐 token 输出。

    前半段与 rag_chat 相同（改写 → 检索 → 重排序 → 构造 prompt），
    之后通过 generate_answer_stream 逐 token yield，最后 yield sources。

    yield 格式：
        {"type": "token", "content": "飞"}       # 逐 token
        {"type": "done", "sources": [...]}       # 流结束 + 来源引用
    """
    # 步骤 0-3：复用 RAG 检索链路
    search_query = rewrite_query(query, history=history)
    candidates = similarity_search_with_metadata(search_query, top_k=top_k * 2)
    contexts = rerank(search_query, candidates, top_k=top_k)
    prompt = _build_prompt(query, contexts)
    sources = _merge_sources(contexts)

    # 步骤 4：流式 LLM 生成
    for token in generate_answer_stream(prompt):
        yield {"type": "token", "content": token}

    # 步骤 5：返回来源引用
    yield {"type": "done", "sources": sources}
