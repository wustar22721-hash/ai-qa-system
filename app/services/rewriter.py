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

_REWRITE_SYSTEM_PROMPT = """你是一个飞书（Feishu/Lark）知识库检索查询改写专家。用户的当前提问可能依赖于对话历史中的上文，包含代词（它、这个、那个、其）、省略主语或延续性追问。你的任务是将当前问题改写为一句独立、完整、可直接用于向量检索的查询语句。

改写规则：
1. 代词消解：将"它 / 这个 / 那个 / 其 / 这些 / 那些"替换为对话历史中明确提到的实体名称
2. 主语补全：如果当前问题是追问且缺少主语，从对话历史中提取并补全
3. 如果当前问题本身已经完整、独立、不依赖上文，则保持原样不做改动
4. 保留用户原始问句中的核心动词和业务关键词
5. 改写后必须是自然的中文问句，不要过度形式化
6. 只输出改写后的一句话，不要有任何解释、前缀、后缀或引号包裹

多轮对话示例：
对话历史：
用户：如何开启飞书会议
助手：在飞书客户端中，打开日历，选择"新建会议"即可创建并开启会议。
当前问题：那么它的功能呢
改写结果：飞书会议有哪些功能

对话历史：
用户：怎么设置多维表格的权限
助手：进入多维表格后，点击右上角"设置"按钮，在权限页面中可以配置。
当前问题：这个怎么关闭
改写结果：多维表格权限设置如何关闭

对话历史：
用户：飞书考勤打卡怎么设置
助手：管理员可以在管理后台的考勤模块中配置打卡规则。
当前问题：能修改吗
改写结果：飞书考勤打卡规则如何修改

无历史的完整问题示例：
当前问题：飞书视频会议如何录制
改写结果：飞书视频会议如何录制

当前问题：怎么下载飞书客户端
改写结果：飞书客户端如何下载安装
"""


def rewrite_query(query: str, history: list[dict[str, str]] | None = None) -> str:
    """将口语化/不完整的 query 改写为独立完整的检索语句。

    结合对话历史进行指代消解：将"它/这个/那个"等代词替换为历史中明确的实体名称，
    补全省略的主语。以改写后的 query 进行向量检索时，能准确命中目标知识。

    Args:
        query: 用户原始问题（可能包含代词或省略主语）
        history: 多轮对话历史，格式 [{"role": "user"/"assistant", "content": "..."}, ...]
                 用于指代消解和主语补全。传入 None 或空列表时降级为直接改写。

    Returns:
        改写后的独立检索语句。如果 LLM 调用失败，返回原始 query 作为降级。
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
