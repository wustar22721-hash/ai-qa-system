"""Agent 主执行器 — 基于 DeepSeek function calling 的 ReAct 循环"""

import json
import logging

from openai import OpenAI

from app.core.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, AGENT_MODEL
from app.services.agent.prompts import TASK_AGENT_SYSTEM_PROMPT
from app.services.agent.state_manager import (
    get_session,
    update_session,
    clear_session,
    add_message,
    get_history,
    set_pending_action,
    get_pending_action,
    clear_pending_action,
)
from app.services.agent.tools import (
    TOOL_DEFINITIONS,
    TOOL_EXECUTORS,
    SENSITIVE_TOOLS,
)

logger = logging.getLogger(__name__)

MAX_TURNS = 5  # 单次请求最多执行 5 轮 LLM 调用


def _build_messages(session_id: str, user_message: str) -> list[dict]:
    """构建 LLM 请求的 messages"""
    history = get_history(session_id)
    messages = [{"role": "system", "content": TASK_AGENT_SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})
    return messages


def _execute_tool(tool_name: str, tool_args: dict) -> str:
    """执行工具并返回结果字符串"""
    executor = TOOL_EXECUTORS.get(tool_name)
    if not executor:
        return f"错误：未知工具 {tool_name}"
    try:
        result = executor(**tool_args)
        if isinstance(result, dict):
            return json.dumps(result, ensure_ascii=False, indent=2)
        return str(result)
    except Exception as e:
        logger.error("工具执行失败 %s(%s): %s", tool_name, tool_args, e)
        return f"工具执行失败：{e}"


def process_confirmation(session_id: str, action: str) -> dict:
    """处理用户对敏感操作的确认或取消。

    由 /agent/confirm 端点调用，不依赖自然语言关键词匹配。
    """
    pending = get_pending_action(session_id)
    if not pending:
        return {"type": "error", "content": "没有待确认的操作"}

    if action == "cancel":
        tool_name = pending["tool"]
        clear_pending_action(session_id)
        add_message(session_id, "user", "取消操作")
        add_message(session_id, "assistant", f"已取消「{tool_name}」操作。还有什么可以帮您的？")
        return {"type": "response", "content": f"已取消「{tool_name}」操作。还有什么可以帮您的？"}

    if action != "confirm":
        return {"type": "error", "content": f"无效的 action: {action}，请使用 confirm 或 cancel"}

    # 执行挂起的操作
    tool_name = pending["tool"]
    tool_args = pending["args"]
    clear_pending_action(session_id)

    if not DEEPSEEK_API_KEY:
        tool_result = _execute_tool(tool_name, tool_args)
        add_message(session_id, "user", f"确认执行 {tool_name}")
        add_message(session_id, "assistant", f"操作已执行，结果：{tool_result}")
        return {"type": "response", "content": f"操作已执行，结果：{tool_result}"}

    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

    add_message(session_id, "user", f"确认执行 {tool_name}")

    history = get_history(session_id)
    messages = [{"role": "system", "content": TASK_AGENT_SYSTEM_PROMPT}]
    clean_history = [m for m in history if m["content"] is not None]
    messages.extend(clean_history)

    tool_result = _execute_tool(tool_name, tool_args)
    messages.append({
        "role": "user",
        "content": f"用户已确认执行 {tool_name}。工具执行结果：{tool_result}\n请根据结果回复用户。",
    })

    try:
        response = client.chat.completions.create(
            model=AGENT_MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=1024,
        )
        content = response.choices[0].message.content or "操作已完成。"
        add_message(session_id, "assistant", content)
        return {"type": "response", "content": content}
    except Exception as e:
        logger.error("确认执行后 LLM 调用失败: %s", e)
        fallback = f"操作已执行，结果：{tool_result}"
        add_message(session_id, "assistant", fallback)
        return {"type": "response", "content": fallback}


def run_agent(session_id: str, user_message: str) -> dict:
    """执行 Agent 主循环。

    返回格式：
        {"type": "response", "content": str}           # 普通文本回复
        {"type": "confirmation_needed", "tool": str, "args": dict, "message": str}  # 需要用户确认
        {"type": "error", "content": str}              # 错误
    """
    if not DEEPSEEK_API_KEY:
        return {"type": "error", "content": "未配置 DEEPSEEK_API_KEY"}

    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

    # 检查是否有待确认的操作和用户是否回复了确认
    pending = get_pending_action(session_id)
    if pending:
        confirm_keywords = ["确认", "是的", "好的", "可以", "行", "同意", "执行", "ok", "yes", "对", "是"]
        cancel_keywords = ["取消", "不要", "算了", "不用", "不", "否", "no"]

        msg_lower = user_message.lower()
        is_confirm = any(kw in msg_lower for kw in confirm_keywords)
        is_cancel = any(kw in msg_lower for kw in cancel_keywords)

        if is_cancel:
            return process_confirmation(session_id, "cancel")
        if is_confirm:
            return process_confirmation(session_id, "confirm")

        # 用户没确认也没取消 — 再次提示确认
        return {
            "type": "confirmation_needed",
            "tool": pending["tool"],
            "args": pending["args"],
            "message": f"请确认是否执行 {pending['tool']}？参数：{json.dumps(pending['args'], ensure_ascii=False)}。回复「确认」或「取消」。",
        }

    # 正常流程：记录用户消息，调用 LLM
    add_message(session_id, "user", user_message)

    messages = _build_messages(session_id, user_message)

    for turn in range(MAX_TURNS):
        try:
            response = client.chat.completions.create(
                model=AGENT_MODEL,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=1024,
            )
        except Exception as e:
            logger.error("LLM 调用失败: %s", e)
            return {"type": "error", "content": f"AI 服务暂时不可用：{e}"}

        choice = response.choices[0]
        msg = choice.message

        # 如果 LLM 要求调用工具
        if msg.tool_calls:
            for tool_call in msg.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                logger.info("LLM 请求工具调用: %s(%s)", tool_name, tool_args)

                # 敏感工具 → 需要用户确认
                if tool_name in SENSITIVE_TOOLS:
                    set_pending_action(session_id, tool_name, tool_args)
                    add_message(session_id, "assistant",
                                f"即将执行 {tool_name}，参数：{json.dumps(tool_args, ensure_ascii=False)}。请确认。")
                    return {
                        "type": "confirmation_needed",
                        "tool": tool_name,
                        "args": tool_args,
                        "message": f"即将执行「{tool_name}」操作，请确认以下信息：\n{json.dumps(tool_args, ensure_ascii=False, indent=2)}\n\n回复「确认」执行，或「取消」放弃。",
                    }

                # 安全工具 → 直接执行
                tool_result = _execute_tool(tool_name, tool_args)
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [tool_call],
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                })
                logger.info("工具执行完成: %s → %s", tool_name, tool_result[:100])

        # 如果 LLM 返回了文本
        elif msg.content:
            add_message(session_id, "assistant", msg.content)
            return {"type": "response", "content": msg.content}

        else:
            logger.warning("LLM 返回空响应")
            return {"type": "response", "content": "抱歉，我暂时无法处理这个请求，请换个方式描述一下？"}

    logger.warning("Agent 循环超过最大轮次 %d", MAX_TURNS)
    return {"type": "error", "content": "处理超时，请简化您的问题后重试。"}
