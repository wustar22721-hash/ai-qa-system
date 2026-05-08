# KBQA — 智能知识库问答系统

让员工告别翻阅上百篇文档，直接用自然语言提问，秒级获得准确答案。

典型场景：企业内部知识库、产品帮助中心、客服辅助系统。支持 Markdown、PDF、Excel 多格式知识库，答案可逐条追溯到原文。

> **技术栈**：Vue 3 · FastAPI · LangChain · ChromaDB · BGE · DeepSeek · PyMuPDF

---

## 效果展示

![效果展示](效果展示图.jpg)

---

## 技术架构

```
┌──────────────────────────────────────────────────────────────┐
│                     Frontend (Vue 3)                          │
│              ChatGPT 风格 UI · Vite · Axios                    │
│                    localhost:5173                              │
└──────────────────────────┬───────────────────────────────────┘
                           │  POST /chat
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                          │
│                     localhost:8000                             │
│                                                               │
│  ┌──────────┐  ┌────────────┐  ┌───────────────────────────┐ │
│  │  API 层  │  │  模型定义   │  │      服务层 (RAG)          │ │
│  │  /chat   │  │  schemas   │  │                             │ │
│  │  /health │  │            │  │  rewriter → vectorstore     │ │
│  └──────────┘  └────────────┘  │      ↓                      │ │
│                                 │  reranker → llm            │ │
│  ┌──────────────────────────┐  │                             │ │
│  │     Ingest Pipeline       │  │  loader_manager            │ │
│  │  load → clean → split     │  │    ├── MarkdownLoader      │ │
│  │    → filter → embed       │  │    ├── PdfLoader           │ │
│  └──────────────────────────┘  │    └── ExcelLoader          │ │
└───────────────────────────────────────────────────────────────┘
       │                  │                    │
       ▼                  ▼                    ▼
┌────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  ChromaDB  │  │  BGE Embedding   │  │  DeepSeek API    │
│  向量存储  │  │  (bge-small-zh)  │  │  (v4-pro / chat) │
└────────────┘  └──────────────────┘  └──────────────────┘
```

---

## 核心特性

### 多格式知识库

| 格式 | 状态 | 实现 |
|------|------|------|
| Markdown (.md) | ✅ 已实现 | 递归读取 + 正则清洗（去图片/链接/视频噪声） |
| PDF (.pdf) | ✅ 已实现 | PyMuPDF 逐页提取 + 页码过滤 |
| Excel (.xlsx) | ✅ 已实现 | pandas 逐 sheet 结构化转自然语言文本 |

所有格式通过统一的 `BaseLoader` 接口接入，新增格式只需实现子类并在注册表加一行。

### 智能检索链路

```
用户提问 → Query Rewriting → 向量检索 Top-10 → 混合 Reranker Top-5 → LLM 生成
```

- **Query Rewriting**：LLM 将口语化短句（"这个怎么关"）改写为完整检索语句（"飞书消息通知的关闭方法"），改写失败自动降级
- **Hybrid Reranker**：70% 向量相似度 + 30% 关键词 bigram 重叠，权限/功能类问题自动加权
- **Metadata 透传**：全链路保留 `document_id`、`chunk_id`、`category`、`file_type` 等字段，支持来源精确追溯

### 评测体系

基于 30 条自动生成的评测数据集，对比两种检索策略：

| 指标 | 纯向量检索 | 向量 + Reranker | 提升 |
|------|-----------|----------------|------|
| Hit@1 | 46.67% | **73.33%** | +26.66% |
| Hit@3 | 76.67% | **80.00%** | +3.33% |
| MRR | 0.6075 | **0.7750** | +0.1675 |

评测脚本 `run_evaluation.py` + 自动生成脚本 `generate_eval_dataset.py` 可实现一键复现。

### AI 产品级前端

- ChatGPT 风格消息气泡（渐变蓝用户气泡 + 白底 AI 气泡）
- 来源引用默认折叠，弱化视觉权重
- 圆形浮动输入框，聚焦时紫色 glow 效果
- Typing dots 加载动画 + AI avatar 呼吸光晕
- 欢迎页推荐问题、对话自动命名、侧边栏删除
- Markdown 渲染优化（代码块、表格、引用块）

---

## 数据规模

| 指标 | 数值 | 说明 |
|------|------|------|
| 源文档 | 439 .md + 3 .pdf + 2 .xlsx | 飞书官方帮助文档，覆盖 12 个产品模块 |
| 文本切片 | ~2,000 条 | chunk_size=500 字符，overlap=100 字符 |
| 向量索引 | 1,772 条 | 经质量过滤后入库 |
| 嵌入维度 | 512 维 | BAAI/bge-small-zh，CPU 推理 |

---

## 项目结构

```
kbqa/
├── app/                              # 后端 (Python FastAPI)
│   ├── main.py                       # 应用入口、生命周期、CORS
│   ├── api/
│   │   └── chat.py                   # POST /chat 接口
│   ├── core/
│   │   └── config.py                 # 环境变量与全局配置
│   ├── models/
│   │   └── schemas.py                # Pydantic 请求/响应模型
│   └── services/
│       ├── loaders/                  # 多格式 loader 集合
│       │   ├── base.py               # 抽象基类 + metadata 约定
│       │   ├── markdown_loader.py    # .md loader
│       │   ├── pdf_loader.py         # .pdf loader (PyMuPDF)
│       │   └── excel_loader.py       # .xlsx loader (pandas)
│       ├── loader_manager.py         # 统一调度：扫描 + 分派 + 聚合
│       ├── ingest.py                 # 入库流水线编排
│       ├── cleaner.py                # Markdown 文本清洗
│       ├── splitter.py               # 文本切片 (LangChain)
│       ├── embedding.py              # BGE 嵌入模型
│       ├── vectorstore.py            # ChromaDB 向量库
│       ├── reranker.py               # 混合重排序
│       ├── rewriter.py               # Query Rewriting
│       ├── llm.py                    # DeepSeek LLM 调用
│       └── rag.py                    # RAG 全流程编排
├── web/                              # 前端 (Vue 3 + Vite)
│   ├── src/
│   │   ├── App.vue                   # 根布局（暗色侧栏 + 主区域）
│   │   ├── views/
│   │   │   └── ChatView.vue          # 聊天主界面
│   │   └── api/
│   │       └── chat.js               # Axios API 客户端
│   ├── vite.config.js                # Vite 配置（含 API 代理）
│   └── package.json
├── 飞书FAQ_知识库/                    # 知识库源文件
│   ├── md/                           # 439 篇 Markdown（12 个分类）
│   ├── pdf/                          # 3 个 PDF 文档
│   └── excel/                        # 2 个 Excel 表格
├── data/chroma/                      # ChromaDB 持久化向量数据
├── eval_dataset.json                 # 评测数据集（30 条 QA）
├── eval_results.md                   # 评测结果报告
├── run_evaluation.py                 # 评测脚本
├── generate_eval_dataset.py          # 评测数据生成脚本
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## 安装与运行

### 环境要求

- Python ≥ 3.10
- Node.js ≥ 18

### 1. 克隆项目

```bash
git clone git@github.com:wustar22721-hash/ai-qa-system.git
cd ai-qa-system
```

### 2. 后端

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate      # Linux/Mac
# .venv\Scripts\activate       # Windows

# 安装依赖
pip install -r requirements.txt

# 配置 API Key
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 启动
python app/main.py
# → http://localhost:8000
# 首次启动自动构建向量索引，后续秒级加载
```

### 3. 前端

```bash
cd web
npm install
npm run dev
# → http://localhost:5173
```

### 4. 评测（可选）

```bash
# 生成评测数据（需 API Key）
python generate_eval_dataset.py

# 运行评测
python run_evaluation.py
```

---

## 环境变量

| 变量 | 必填 | 说明 | 默认值 |
|------|------|------|--------|
| `DEEPSEEK_API_KEY` | ✅ | DeepSeek API 密钥 | — |
| `DEEPSEEK_BASE_URL` | — | API 地址 | `https://api.deepseek.com/v1` |
| `LLM_MODEL` | — | 生成模型 | `deepseek-v4-pro` |
| `REWRITER_MODEL` | — | 改写模型（需非推理型） | `deepseek-chat` |
| `CHROMA_PERSIST_DIR` | — | ChromaDB 存储路径 | `data/chroma` |
| `HF_ENDPOINT` | — | HuggingFace 镜像 | `https://hf-mirror.com` |

---

## API 接口

### `POST /chat`

```json
// 请求
{
  "query": "飞书会议如何开启自动字幕？",
  "history": null
}

// 响应
{
  "answer": "在飞书会议中开启自动字幕的步骤如下：\n1. 加入会议后...",
  "sources": [
    {
      "file": "开启字幕与翻译.md",
      "content": "会议中点击底部工具栏的...",
      "chunk_ids": ["a091674bfd3d_2", "a091674bfd3d_3"]
    }
  ]
}
```

### `GET /health`

```json
{ "status": "ok" }
```

---

## 检索评测

评测数据集 `eval_dataset.json` 包含 30 条跨 12 个分类的真实场景 QA 对，由 LLM 自动生成并人工核验。

| 指标 | 纯向量检索 | 向量 + Reranker | 提升 |
|------|-----------|----------------|------|
| Hit@1 | 46.67% | **73.33%** | +26.66% |
| Hit@3 | 76.67% | **80.00%** | +3.33% |
| MRR | 0.6075 | **0.7750** | +0.1675 |

- Reranker 在 30 条评测中 10 次优于纯向量检索，0 次差于
- 5 条 Bad Case 双方均未命中，已定位为口语化短 query 问题（已通过 Query Rewriting 改善）

---

## 项目亮点

### 工程方面

- **模块化 RAG 管道**：loader → cleaner → splitter → embed → vectorstore → reranker → llm，七个独立服务可单独替换
- **LangChain 作为组件库**：仅用于文本切片、嵌入封装、向量库集成，业务逻辑手写
- **无 GPU 可运行**：BGE-small-zh CPU 推理 + 自定义轻量 reranker
- **感知式启动**：首次自动构建向量库，后续启动 5-10 秒即就绪
- **多格式 loader 架构**：统一 `BaseLoader` 接口 + Registry 模式，新增格式零侵入
- **ChatGPT 风格前端**：Vue 3 纯 CSS 实现消息气泡、浮动输入框、typing dots 动画

### AI 方面

- **Query Rewriting**：口语化短句 → 完整检索语句，类似"这个怎么关"改写为"飞书消息通知的关闭方法"
- **Hybrid Reranker**：向量相似度 + 关键词 bigram + 领域加权，Hit@1 从 46.67% 提升至 73.33%
- **Metadata 全链路**：document_id、chunk_id、category、file_type 从入库到 API 返回完整保留
- **可溯源生成**：System Prompt 约束逐条标注来源，前端可展开原文验证

---

## 路线图

- [x] Markdown 知识库 + 向量检索 + Reranker
- [x] 多格式支持（PDF / Excel）
- [x] Query Rewriting 口语化改写
- [x] 评测体系（30 条 QA + Hit@K + MRR）
- [x] AI 产品级前端 UI
- [x] Metadata 全链路透传
- [ ] 多轮对话（上下文记忆 + 追问理解）
- [ ] Hybrid BM25 + Dense 检索
- [ ] Category 过滤检索
- [ ] Docker 一键部署
- [ ] 飞书机器人接入

---

## License

MIT
