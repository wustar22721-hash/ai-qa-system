"""
Query Rewriting 模块

在检索前调用 LLM 将口语化、省略主语/实体的用户问题改写为
独立、完整、包含明确业务实体的检索语句，提升向量检索命中率。

对改写失败（超时、API 异常等）自动降级，返回原始 query。
"""

import logging

from openai import OpenAI

from app.core.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, REWRITER_MODEL

logger = logging.getLogger(__name__)

_REWRITE_SYSTEM_PROMPT = """你是一个飞书（Feishu/Lark）知识库检索优化专家。用户的提问通常口语化、省略主语、依赖上下文。你的任务是将用户问题改写为一句独立、完整、信息充分的检索语句。

改写规则：
1. 把代词和模糊指代替换为具体的业务实体名称（如"这个怎么用"→"飞书多维表格如何使用"）
2. 补充缺失的主语和宾语，让问题脱离上下文也能被准确理解
3. 保留用户问句中的核心动词和业务关键词
4. 改写后必须是自然的中文问句，不要过度形式化
5. 只输出改写后的一句话，不要有任何解释、前缀或后缀

示例：
- "这个怎么下载" → "飞书电脑端和移动端客户端的下载安装方法"
- "怎么设置" → "飞书考勤打卡规则如何设置"
- "他看不到" → "飞书云文档中协作者无法查看文件的权限问题排查"
- "能关掉吗" → "飞书视频会议AI视图功能的关闭方法"
- "怎么开" → "飞书管理后台新功能权限如何开启"
"""


def rewrite_query(query: str, history: list[dict[str, str]] | None = None) -> str:
    """将口语化/不完整的 query 改写为独立完整的检索语句。

    Args:
        query: 用户原始问题
        history: 多轮对话历史，格式 [{"role": "user"/"assistant", "content": "..."}, ...]
                 当前预留，用于未来多轮对话下的指代消解。

    Returns:
        改写后的检索语句。如果 LLM 调用失败，返回原始 query 作为降级。
    """
    if not DEEPSEEK_API_KEY or "your-deepseek-key" in DEEPSEEK_API_KEY:
        logger.warning("[Query Rewriting] 未配置 DEEPSEEK_API_KEY，使用原始 query")
        return query

    # 构建用户消息
    messages = [{"role": "system", "content": _REWRITE_SYSTEM_PROMPT}]

    # 如果有历史对话，拼入上下文（未来扩展）
    if history:
        recent = history[-6:]  # 取最近 3 轮（6 条）
        for msg in recent:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })
        messages.append({
            "role": "user",
            "content": f"基于以上对话上下文，请改写当前问题为独立的检索语句：{query}",
        })
    else:
        messages.append({"role": "user", "content": query})

    try:
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        response = client.chat.completions.create(
            model=REWRITER_MODEL,
            messages=messages,
            temperature=0.1,       # 低温度，确保改写稳定
            max_tokens=256,        # 改写只需一句话，不需要太长
            timeout=10.0,          # 10 秒超时
        )
        content = response.choices[0].message.content
        if content and content.strip():
            rewritten = content.strip()
            # 清理可能的 markdown 引号包裹
            if rewritten.startswith('"') and rewritten.endswith('"'):
                rewritten = rewritten[1:-1]
            logger.info("[Query Rewriting] 原始问题: %s", query)
            logger.info("[Query Rewriting] 改写后检索词: %s", rewritten)
            return rewritten

        logger.warning("[Query Rewriting] LLM 返回空内容，降级使用原始 query")
        return query

    except Exception as e:
        logger.warning("[Query Rewriting] 改写请求失败 (%s)，降级使用原始 query: %s", e, query)
        return query
