"""RAG 知识库问答系统 — FastAPI 入口

启动方式：
    python -m app.main          # 推荐
    python app/main.py          # 兼容
    uvicorn app.main:app --reload
"""

import sys
from pathlib import Path

# 确保项目根在 sys.path（兼容 python app/main.py 直接运行）
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import logging
from contextlib import asynccontextmanager

import chromadb
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.core.config import CHROMA_PERSIST_DIR, KNOWLEDGE_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def _init_vector_store():
    """初始化向量库：已有则加载，否则从零构建"""
    from app.services.vectorstore import load_vector_store

    # 已有数据则直接加载
    if Path(CHROMA_PERSIST_DIR).is_dir():
        try:
            client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
            col = client.get_collection("langchain")
            if col.count() > 0:
                logger.info("向量库已有 %d 条记录，直接从磁盘加载", col.count())
                load_vector_store()
                return
        except Exception:
            pass

    # 从零构建：全量 ingest 流水线
    from app.services.ingest import run_ingest

    logger.info("向量库为空，开始全量构建...")
    run_ingest(KNOWLEDGE_DIR)
    logger.info("向量库构建完成")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _init_vector_store()
    yield


app = FastAPI(
    title="KBQA",
    description="基于本地 Markdown 知识库的 RAG 问答系统",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(_project_root / "app")],
    )
