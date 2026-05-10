"""对话接口"""

import logging

from fastapi import APIRouter

from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    SourceItem,
    AgentChatRequest,
    AgentChatResponse,
    ConfirmRequest,
)
from app.services.rag import rag_chat
from app.services.agent.router import classify_intent
from app.services.agent.agent_executor import run_agent, process_confirmation
from app.services.agent.state_manager import clear_session, get_session

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    result = rag_chat(req.query, history=req.history)
    return ChatResponse(
        answer=result["answer"],
        sources=[
            SourceItem(file=s["file"], content=s["content"], chunk_ids=s.get("chunk_ids", []))
            for s in result["sources"]
        ],
    )


@router.post("/agent/chat", response_model=AgentChatResponse)
async def agent_chat(req: AgentChatRequest) -> AgentChatResponse:
    """Agent 对话接口：自动路由知识咨询 / 任务执行"""
    session = get_session(req.session_id)

    # 如果已有活跃的任务会话（有历史记录）→ 直接走 agent 流程
    has_active_task = (
        session.get("current_intent") == "task"
        and len(session.get("history", [])) > 0
    )

    if has_active_task:
        intent = "task"
    else:
        intent = classify_intent(req.query)

    if intent == "knowledge":
        result = rag_chat(req.query, history=req.history)
        return AgentChatResponse(
            type="response",
            content=result["answer"],
            sources=[
                SourceItem(file=s["file"], content=s["content"], chunk_ids=s.get("chunk_ids", []))
                for s in result["sources"]
            ],
        )

    # 任务执行模式
    session["current_intent"] = "task"
    result = run_agent(req.session_id, req.query)

    return AgentChatResponse(
        type=result["type"],
        content=result.get("content", ""),
        tool=result.get("tool"),
        args=result.get("args"),
    )


@router.post("/agent/confirm", response_model=AgentChatResponse)
async def agent_confirm(req: ConfirmRequest) -> AgentChatResponse:
    """确认或取消 Agent 的待确认操作"""
    if req.action not in ("confirm", "cancel"):
        return AgentChatResponse(type="error", content=f"无效的 action: {req.action}")

    result = process_confirmation(req.session_id, req.action)
    return AgentChatResponse(
        type=result["type"],
        content=result.get("content", ""),
    )


@router.post("/agent/reset")
async def agent_reset(session_id: str = "default"):
    """重置 Agent 会话"""
    clear_session(session_id)
    return {"status": "ok", "message": f"会话 {session_id} 已重置"}
