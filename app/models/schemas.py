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
