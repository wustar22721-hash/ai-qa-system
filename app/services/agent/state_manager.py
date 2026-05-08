"""会话状态管理 — 管理多轮对话的槽位填充和确认状态"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# 全局会话存储
sessions: dict[str, dict] = {}


def get_session(session_id: str) -> dict:
    """获取会话状态，不存在则创建默认状态"""
    if session_id not in sessions:
        sessions[session_id] = {
            "history": [],  # [{"role": "user"/"assistant"/"tool", "content": "..."}, ...]
            "collected_info": {},  # 已收集的工单字段
            "pending_action": None,  # 待确认的操作: {"tool": str, "args": dict}
            "current_intent": None,  # "knowledge" | "task"
        }
    return sessions[session_id]


def update_session(session_id: str, **kwargs) -> dict:
    """更新会话状态的指定字段"""
    session = get_session(session_id)
    for key, value in kwargs.items():
        if key == "collected_info" and isinstance(value, dict):
            session["collected_info"].update(value)
        else:
            session[key] = value
    return session


def clear_session(session_id: str):
    """清除会话"""
    sessions.pop(session_id, None)
    logger.info("会话已清除: %s", session_id)


def add_message(session_id: str, role: str, content: str):
    """向会话历史追加一条消息"""
    session = get_session(session_id)
    session["history"].append({"role": role, "content": content})


def get_history(session_id: str) -> list[dict[str, str]]:
    """获取会话历史"""
    return get_session(session_id)["history"]


def set_pending_action(session_id: str, tool_name: str, tool_args: dict):
    """设置待确认的操作"""
    update_session(session_id, pending_action={"tool": tool_name, "args": tool_args})


def get_pending_action(session_id: str) -> dict | None:
    """获取待确认的操作"""
    return get_session(session_id).get("pending_action")


def clear_pending_action(session_id: str):
    """清除待确认的操作"""
    update_session(session_id, pending_action=None)
