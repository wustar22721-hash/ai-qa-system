"""对话接口 —— 提供 HTTP API 让前端与 RAG / Agent 系统交互

这个文件定义了所有面向用户的 HTTP 接口（路由），是整个系统的"门面"：
    - 用户通过前端发送请求 → 这个文件接收请求 → 调用后端服务 → 返回结果给前端

接口总览：
    POST /chat           普通问答（直接走 RAG 检索 + LLM 生成）
    POST /agent/chat     Agent 问答（先判断意图：知识问答 / 任务执行，然后走不同流程）
    POST /agent/confirm  确认 Agent 的待执行操作（批准/取消）
    POST /agent/reset    重置 Agent 会话（清除历史记录）
"""

# ============================================================
# 导入依赖
# ============================================================

import json
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

# 请求/响应数据模型（dataclass 风格，定义了请求和响应的字段结构）
from app.models.schemas import (
    ChatRequest,       # 普通聊天请求：{query, history?}
    ChatResponse,      # 普通聊天响应：{answer, sources[]}
    SourceItem,        # 来源条目：{file, content, chunk_ids}
    AgentChatRequest,  # Agent 聊天请求：{query, session_id}
    AgentChatResponse, # Agent 聊天响应：{type, content, tool?, args?, sources?}
    ConfirmRequest,    # 确认请求：{session_id, action}
)

# 后端服务模块
from app.services.rag import rag_chat, rag_chat_stream  # RAG 问答
from app.services.agent.router import classify_intent  # 意图分类：判断用户想"问知识"还是"执行任务"
from app.services.agent.agent_executor import run_agent, process_confirmation  # Agent 执行器
from app.services.agent.state_manager import clear_session, get_session  # 会话管理

logger = logging.getLogger(__name__)

# 创建路由器实例（后续所有接口都注册到这个路由上，由 main.py 通过 include_router 挂载）
router = APIRouter()


# ============================================================
# 接口1：普通 RAG 问答 — POST /chat
# ============================================================

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """
    接收用户问题，走完整的 RAG 流程并返回答案。

    流程简述：
        用户问题 → 改写查询语句 → 向量检索 → 重排序 → 拼接上下文 → LLM 生成答案

    参数：
        req.query: 用户输入的原始问题
        req.history: 对话历史（可选），用于理解上下文，例如用户追问"那它的功能呢？"

    返回值：
        ChatResponse:
            answer:  LLM 生成的回答文本
            sources: 回答引用的知识库来源列表（文件、内容片段、chunk ID）
    """
    # 调用 rag_chat 函数，它封装了完整的 RAG 流水线
    result = rag_chat(req.query, history=req.history)

    # 将 rag_chat 返回的 dict 转换为 API 规范的 ChatResponse 格式
    return ChatResponse(
        answer=result["answer"],
        sources=[
            # 每个来源文件生成一个 SourceItem
            SourceItem(
                file=s["file"],                 # 来源文件名（如 "权限说明.md"）
                content=s["content"],            # 该文件的引用内容片段
                chunk_ids=s.get("chunk_ids", []),  # 该片段对应的 chunk ID 列表（用于前端高亮等）
            )
            for s in result["sources"]
        ],
    )


# ============================================================
# 接口2：流式 RAG 问答 — POST /chat/stream
# ============================================================

@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """流式 RAG 问答接口，逐 token 通过 SSE 推送，前端实现打字机效果。

    SSE 事件格式：
        data: {"type":"token","content":"飞"}

        data: {"type":"done","sources":[...]}

    流程：rewrite → retrieval → rerank → build_prompt → LLM stream
    RAG 检索链路与同步 /chat 完全一致，仅 LLM 生成阶段改为流式。
    """
    async def event_generator():
        try:
            for event in rag_chat_stream(req.query, history=req.history):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception:
            logger.exception("[Stream] rag_chat_stream 异常中断")
            yield f"data: {json.dumps({'type': 'error', 'content': '流式生成出错，请重试'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
        },
    )


# ============================================================
# 接口3：Agent 对话 — POST /agent/chat
# ============================================================

@router.post("/agent/chat", response_model=AgentChatResponse)
async def agent_chat(req: AgentChatRequest) -> AgentChatResponse:
    """
    Agent 对话接口：自动判断用户意图，路由到不同的处理流程。

    两种意图：
        1. "knowledge"（知识问答）：和普通 /chat 一样，走 RAG 检索 + 生成答案
        2. "task"（任务执行）：走 Agent 流程，可能涉及工具调用、多轮交互、确认机制

    会话保持：
        通过 session_id 区分不同用户/会话，同一个 session_id 的多轮对话会共享上下文。

    参数：
        req.query:      用户输入
        req.session_id: 会话 ID（用于保持多轮对话状态）

    返回值：
        AgentChatResponse:
            type:    响应类型："response"（直接回复）/ "confirm"（需要确认）/ "error"（错误）/ "done"（任务完成）
            content: 文本内容
            tool:    如果涉及工具调用，工具名称
            args:    如果涉及工具调用，工具参数
            sources: 如果是知识问答，引用的来源列表
    """
    # 获取或创建当前会话（session 是一个 dict，存储了会话的所有状态信息）
    session = get_session(req.session_id)

    # --- 意图判断 ---
    # 规则：如果当前会话已经标记为"任务模式"且有多轮历史，则继续走任务流程
    # 这样可以保持任务执行中的多轮对话连续性
    has_active_task = (
        session.get("current_intent") == "task"
        and len(session.get("history", [])) > 0
    )

    if has_active_task:
        # 已有活跃任务：直接沿用"任务"意图，不再重新分类
        intent = "task"
    else:
        # 新会话或非任务会话：调用 LLM 判断用户意图
        # classify_intent 会分析用户的输入，判断是"想问知识"还是"想做操作"
        intent = classify_intent(req.query)

    # --- 根据意图分发处理 ---

    # 分支 A：知识问答 → 走 RAG 流程（和 /chat 接口完全一样）
    if intent == "knowledge":
        result = rag_chat(req.query, history=req.history)
        return AgentChatResponse(
            type="response",        # 直接回复，不需要确认
            content=result["answer"],
            sources=[
                SourceItem(file=s["file"], content=s["content"], chunk_ids=s.get("chunk_ids", []))
                for s in result["sources"]
            ],
        )

    # 分支 B：任务执行 → 走 Agent 流程
    # Agent 流程可能涉及：
    #   1. 理解用户要做什么 → 2. 选择合适的工具 → 3. 执行工具 → 4. 返回结果
    #   对于敏感操作（如删除），还会向用户确认后才执行
    session["current_intent"] = "task"               # 标记会话为任务模式
    result = run_agent(req.session_id, req.query)    # 启动 Agent 执行

    return AgentChatResponse(
        type=result["type"],              # 响应类型
        content=result.get("content", ""),  # 文本内容
        tool=result.get("tool"),            # 工具名称（如有）
        args=result.get("args"),            # 工具参数（如有）
    )


# ============================================================
# 接口3：确认操作 — POST /agent/confirm
# ============================================================

@router.post("/agent/confirm", response_model=AgentChatResponse)
async def agent_confirm(req: ConfirmRequest) -> AgentChatResponse:
    """
    确认或取消 Agent 的待执行操作。

    为什么需要确认？
        Agent 执行某些操作（如删除数据、修改设置）前会暂停并请求用户确认。
        这是一个安全机制，防止误操作。

    参数：
        req.session_id: 会话 ID
        req.action:     "confirm"（批准执行）或 "cancel"（取消执行）

    返回值：
        AgentChatResponse:
            type:    "done"（确认后已完成执行）/ "error"（出错）
            content: 执行结果说明
    """
    # 校验 action 参数
    if req.action not in ("confirm", "cancel"):
        return AgentChatResponse(type="error", content=f"无效的 action: {req.action}")

    # 处理确认/取消逻辑
    result = process_confirmation(req.session_id, req.action)
    return AgentChatResponse(
        type=result["type"],
        content=result.get("content", ""),
    )


# ============================================================
# 接口4：重置会话 — POST /agent/reset
# ============================================================

@router.post("/agent/reset")
async def agent_reset(session_id: str = "default"):
    """
    重置 Agent 会话，清除所有对话历史和状态。

    用途：
        - 用户想开始一个全新的对话（不受之前上下文影响）
        - 调试时快速清空状态

    参数：
        session_id: 要重置的会话 ID（默认 "default"）

    返回值：
        {status: "ok", message: "会话 xxx 已重置"}
    """
    clear_session(session_id)  # 清除该会话的所有内存数据（历史、意图、待确认操作等）
    return {"status": "ok", "message": f"会话 {session_id} 已重置"}
