"""Pydantic 数据模型"""

from pydantic import BaseModel, Field


class SourceItem(BaseModel):
    file: str = Field(..., description="来源文件名")
    content: str = Field(..., description="匹配到的 chunk 文本")


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, description="用户问题")


class ChatResponse(BaseModel):
    answer: str = Field(..., description="LLM 生成的回答")
    sources: list[SourceItem] = Field(default_factory=list, description="检索到的来源（含文件名和内容）")
