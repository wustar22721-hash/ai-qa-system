"""Pydantic 数据模型"""

from pydantic import BaseModel, Field


class SourceItem(BaseModel):
    file: str = Field(..., description="来源文件名")
    content: str = Field(..., description="匹配到的 chunk 文本")
    chunk_ids: list[str] = Field(default_factory=list, description="命中 chunk 的 ID 列表")


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, description="用户问题")
    history: list[dict[str, str]] | None = Field(
        default=None, description="多轮对话历史 [{\"role\":\"user\"/\"assistant\",\"content\":\"...\"}]"
    )


class ChatResponse(BaseModel):
    answer: str = Field(..., description="LLM 生成的回答")
    sources: list[SourceItem] = Field(default_factory=list, description="检索到的来源（含文件名和内容）")


# ---------- Agent 相关模型 ----------

class AgentChatRequest(BaseModel):
    query: str = Field(..., min_length=1, description="用户问题")
    session_id: str = Field(default="default", description="会话 ID，用于多轮对话状态管理")
    history: list[dict[str, str]] | None = Field(
        default=None, description="多轮对话历史（预留，agent 内部管理状态）"
    )


class AgentChatResponse(BaseModel):
    type: str = Field(..., description="响应类型：response / confirmation_needed / error")
    content: str = Field(default="", description="文本回复内容")
    sources: list[SourceItem] = Field(default_factory=list, description="知识库来源（knowledge 模式）")
    tool: str | None = Field(default=None, description="待确认的工具名称")
    args: dict | None = Field(default=None, description="待确认的工具参数")


class ConfirmRequest(BaseModel):
    session_id: str = Field(..., description="会话 ID")
    action: str = Field(..., description="confirm 或 cancel")
