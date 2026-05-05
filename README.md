# 🤖 KBQA — 智能知识库问答系统

基于 **RAG（检索增强生成）** 架构的企业级知识库问答系统。以飞书（Lark）帮助文档为知识底座，结合向量检索、混合重排序与 DeepSeek 大模型，实现精准、可溯源的中文知识问答。
---

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (Vue 3)                     │
│              Element Plus · Axios · Vite                 │
│                   localhost:5173                         │
└────────────────────────┬────────────────────────────────┘
                         │  POST /chat
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  Backend (FastAPI)                       │
│                   localhost:8000                         │
│                                                         │
│   ┌──────────┐  ┌──────────┐  ┌──────────────────┐     │
│   │  API 层  │  │ 模型定义 │  │    服务层 (RAG)   │     │
│   │  /chat   │  │ schemas  │  │  loader → cleaner │     │
│   │  /health │  │          │  │    ↓              │     │
│   └──────────┘  └──────────┘  │  splitter → embed │     │
│                                │    ↓              │     │
│                                │  vectorstore →    │     │
│                                │  reranker → llm   │     │
│                                └──────────────────┘     │
└─────────────────────────────────────────────────────────┘
     │                    │                    │
     ▼                    ▼                    ▼
┌──────────┐  ┌──────────────────┐  ┌──────────────────┐
│ ChromaDB │  │  BGE Embedding   │  │  DeepSeek API    │
│ 向量存储 │  │  (bge-small-zh)  │  │  (v4-pro)        │
└──────────┘  └──────────────────┘  └──────────────────┘
```

---

## ✨ 核心功能

| 功能 | 说明 |
|------|------|
| **知识库问答** | 基于 439 篇飞书官方文档，回答飞书功能使用、权限配置、操作流程等问题 |
| **混合检索** | 向量相似度 + 关键词重叠双路重排序，提升检索精准度 |
| **领域增强** | 针对权限/功能类查询的专属 boost 策略，自动区分"能不能做"和"怎么做" |
| **来源追溯** | 每个回答标注参考文档来源，前端展示可展开的引用卡片 |

---

## 📁 项目结构

```
kbqa/
├── app/                          # 后端 (Python FastAPI)
│   ├── main.py                   # 应用入口、生命周期、CORS
│   ├── api/
│   │   └── chat.py               # POST /chat 接口
│   ├── core/
│   │   └── config.py             # 环境变量与全局配置
│   ├── models/
│   │   └── schemas.py            # Pydantic 请求/响应模型
│   └── services/
│       ├── loader.py             # 递归加载 Markdown 知识文件
│       ├── cleaner.py            # 文本清洗（去图片/链接/时间戳）
│       ├── splitter.py           # LangChain 文本切片
│       ├── embedding.py          # BGE 中文嵌入模型
│       ├── vectorstore.py        # ChromaDB 向量库构建/检索
│       ├── reranker.py           # 混合重排序（向量 + 关键词）
│       ├── llm.py                # DeepSeek LLM 调用
│       └── rag.py                # RAG 全流程编排
├── web/                          # 前端 (Vue 3 + Vite)
│   ├── src/
│   │   ├── App.vue               # 根布局（侧栏 + 主区域）
│   │   ├── views/
│   │   │   └── ChatView.vue      # 聊天主界面
│   │   └── api/
│   │       └── chat.js           # Axios API 客户端
│   ├── vite.config.js            # Vite 配置（含 API 代理）
│   └── package.json
├── 飞书FAQ_知识库_MD/             # 知识库源文件（12 类 439 篇）
├── data/chroma/                  # ChromaDB 持久化向量数据
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## 🚀 安装与运行

### 环境要求

- Python ≥ 3.10
- Node.js ≥ 18
- Git

### 1. 克隆项目

```bash
git clone git@github.com:wustar22721-hash/ai-qa-system.git
cd ai-qa-system
```

### 2. 后端安装

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate    # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 DEEPSEEK_API_KEY
```

### 3. 启动后端

```bash
python app/main.py
# 服务启动于 http://localhost:8000
# 首次启动自动构建向量索引，后续启动秒级加载
```

### 4. 前端安装与启动

```bash
cd web
npm install
npm run dev
# 开发服务器启动于 http://localhost:5173
```

访问 `http://localhost:5173`，在对话框中输入飞书相关问题即可体验。

---

## 🔧 环境变量说明

在项目根目录创建 `.env` 文件（参考 `.env.example`）：

| 变量名 | 必填 | 说明 | 默认值 |
|--------|------|------|--------|
| `DEEPSEEK_API_KEY` | ✅ | DeepSeek API 密钥 | `""` |
| `DEEPSEEK_BASE_URL` | - | API 地址 | `https://api.deepseek.com/v1` |
| `LLM_MODEL` | - | 模型名称 | `deepseek-v4-pro` |
| `CHROMA_PERSIST_DIR` | - | ChromaDB 持久化路径 | `data/chroma` |
| `HF_ENDPOINT` | - | HuggingFace 镜像（国内加速） | `https://hf-mirror.com` |

---

## 📡 API 接口

### `POST /chat`

**请求体：**
```json
{
  "query": "飞书会议如何开启自动字幕？"
}
```

**响应体：**
```json
{
  "answer": "在飞书会议中开启自动字幕的步骤如下：\n1. 加入会议后，点击底部工具栏的「更多」...",
  "sources": [
    {
      "file": "开启字幕与翻译.md",
      "content": "会议中点击底部工具栏的..."
    }
  ]
}
```

### `GET /health`

```json
{ "status": "ok" }
```

---

## 💡 项目亮点

### 工程角度

- **模块化服务设计**：加载 → 清洗 → 切片 → 嵌入 → 检索 → 重排序 → 生成，每个环节独立可替换
- **无 GPU 依赖**：BGE-small-zh 在 CPU 上运行，混合重排序免去交叉编码器模型
- **智能启动缓存**：首次构建向量库后持久化到磁盘，后续启动直接加载
- **前后端分离**：Vue 3 + FastAPI，Vite 代理解决开发跨域

### AI 角度

- **混合检索策略**：向量语义相似度（70%）+ 关键词 bigram 重叠（30%），兼顾语义与字面匹配
- **领域自适应**：检测权限/功能类查询，自动增强管控关键词权重，保证至少一条管控相关上下文进入 top-K
- **严格溯源指令**：System Prompt 要求模型逐条引用来源文件名，前端以可展开卡片展示引用原文
- **中文优化**：BGE 中文嵌入模型 + DeepSeek-v4-pro 中文大模型 + 中文分词关键词重叠

---

## 📸 效果展示

![效果展示](效果展示图.jpg)

---

## 🗺️ 路线图

- [ ] 对话历史持久化与多轮对话支持
- [ ] 知识库热更新（无需重启服务）
- [ ] Docker 一键部署
- [ ] 飞书机器人接入

---

## 📄 License

MIT
