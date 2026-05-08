"""意图路由器 — 判断用户输入是知识咨询还是任务执行"""

import logging

from openai import OpenAI

from app.core.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, LLM_MODEL
from app.services.agent.prompts import INTENT_CLASSIFY_PROMPT

logger = logging.getLogger(__name__)

# 快速关键词匹配（无需调用 LLM）
_TASK_KEYWORDS = [
    "创建工单", "新建工单", "帮我创建", "工单", "报修", "故障上报",
    "查询员工", "查一下", "帮我查", "员工信息",
    "发送通知", "发通知", "通知一下", "发消息",
    "帮我提交", "帮我处理",
]

_KNOWLEDGE_KEYWORDS = [
    "怎么", "如何", "什么是", "是什么", "介绍", "说明", "教程",
    "步骤", "方法", "功能", "在哪里", "能不能", "可以吗",
]


def _quick_classify(message: str) -> str | None:
    """快速关键词分类，无法判断时返回 None"""
    msg = message.strip()
    for kw in _TASK_KEYWORDS:
        if kw in msg:
            return "task"
    for kw in _KNOWLEDGE_KEYWORDS:
        if kw in msg:
            return "knowledge"
    return None


def classify_intent(message: str) -> str:
    """判断用户意图，返回 'knowledge' 或 'task'"""
    # 1. 快速关键词匹配
    quick = _quick_classify(message)
    if quick:
        logger.info("关键词匹配 → %s", quick)
        return quick

    # 2. LLM 分类
    if not DEEPSEEK_API_KEY:
        return "knowledge"  # 默认走知识库

    try:
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": INTENT_CLASSIFY_PROMPT},
                {"role": "user", "content": message},
            ],
            temperature=0.0,
            max_tokens=10,
            timeout=10.0,
        )
        content = response.choices[0].message.content
        result = content.strip().lower() if content else "knowledge"
        if result not in ("knowledge", "task"):
            result = "knowledge"
        logger.info("LLM 分类 → %s", result)
        return result
    except Exception as e:
        logger.warning("意图分类 LLM 调用失败 (%s)，默认走知识库", e)
        return "knowledge"
