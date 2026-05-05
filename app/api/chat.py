"""对话接口"""

from fastapi import APIRouter

from app.models.schemas import ChatRequest, ChatResponse, SourceItem
from app.services.rag import rag_chat

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    result = rag_chat(req.query)
    return ChatResponse(
        answer=result["answer"],
        sources=[SourceItem(file=s["file"], content=s["content"]) for s in result["sources"]],
    )
