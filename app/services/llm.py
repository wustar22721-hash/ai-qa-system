"""LLM 调用模块 — DeepSeek API（兼容 OpenAI 格式）"""

import logging

from openai import OpenAI

from app.core.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, LLM_MODEL

logger = logging.getLogger(__name__)


def generate_answer(prompt: str, max_retries: int = 2) -> str:
    """调用 DeepSeek 生成回答，空响应自动重试，token 不足时告警"""
    if not DEEPSEEK_API_KEY:
        return "错误：未配置 DEEPSEEK_API_KEY，请检查 .env 文件"

    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2048,
            )
            choice = response.choices[0]
            content = choice.message.content
            if choice.finish_reason == "length":
                logger.warning("回答被截断（max_tokens 不足），建议增大 max_tokens")
            if content:
                return content
            logger.warning("API 返回空内容，重试 %d/%d", attempt + 1, max_retries)
        except Exception as e:
            logger.error("DeepSeek API 调用失败: %s", e)
            return f"抱歉，AI 服务暂时不可用，请稍后重试。（错误信息：{e}）"

    return "抱歉，AI 服务暂时不可用，请稍后重试。"
