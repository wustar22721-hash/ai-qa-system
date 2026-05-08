"""
自动生成 RAG 评测数据集

调用 DeepSeek API，基于知识库源文档，自动生成 30 个真实场景下的 QA 对，
每条数据包含：问题、标准答案、正确的源文档文件名、所属分类。

用法：
    python generate_eval_dataset.py
    输出：eval_dataset.json
"""

import json
import logging
import random
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DIR = BASE_DIR / "飞书FAQ_知识库_MD"
OUTPUT_FILE = BASE_DIR / "eval_dataset.json"

API_KEY = __import__("os").getenv("DEEPSEEK_API_KEY", "")
BASE_URL = __import__("os").getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
MODEL = __import__("os").getenv("LLM_MODEL", "deepseek-v4-pro")

TOTAL_QA = 30
MAX_DOC_CHARS = 3500  # 每篇文档最多给 LLM 看这么多字符
FILES_PER_BATCH = 5   # 每批给 LLM 的文档数
QA_PER_BATCH = 5      # 每批生成 QA 对数量

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 文档加载 & 清洗（复用现有逻辑的简化版）
# ---------------------------------------------------------------------------
_IMG_PATTERN = re.compile(r"!\[.*?\]\(.*?\)")
_LINK_PATTERN = re.compile(r"\[([^\]]*?)\]\(.*?\)")
_TIMESTAMP_PATTERN = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")
_IMG_SIZE_PATTERN = re.compile(r"\d+px\s*\|\s*\d+px\s*\|\s*reset", re.IGNORECASE)
_ZERO_WIDTH_PATTERN = re.compile(r"[​‌‍‎‏﻿]")
_TABLE_SEP_PATTERN = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$")
_PURE_SYMBOL_PATTERN = re.compile(r"^[\s\|\-—–·•●◎○□■△▲▽▼☆★♦♥♣♠✓✗☐☑☒⬜✅❌🔖📌📎📝�]{1,5}$")
_MULTI_BLANK_PATTERN = re.compile(r"\n{3,}")

_VIDEO_KEYWORDS = ["播放", "倍速", "快进", "快退", "暂停", "静音", "画中画", "全屏", "小窗"]
_VIDEO_LINE_PATTERN = re.compile(
    r"^.*?(" + "|".join(map(re.escape, _VIDEO_KEYWORDS)) + r").*?$", re.IGNORECASE)
_VIDEO_INLINE_PATTERN = re.compile(
    r"\b(" + "|".join(map(re.escape, _VIDEO_KEYWORDS)) + r")\b", re.IGNORECASE)


def clean_markdown(text: str) -> str:
    """清洗 Markdown（与 app/services/cleaner.py 一致）"""
    text = _IMG_PATTERN.sub("", text)
    text = _LINK_PATTERN.sub(r"\1", text)
    text = _IMG_SIZE_PATTERN.sub("", text)
    text = _ZERO_WIDTH_PATTERN.sub("", text)
    text = _TIMESTAMP_PATTERN.sub("", text)

    lines = text.split("\n")
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            clean_lines.append("")
            continue
        if _PURE_SYMBOL_PATTERN.match(stripped):
            continue
        if _TABLE_SEP_PATTERN.match(stripped):
            continue
        if _VIDEO_LINE_PATTERN.match(stripped):
            remaining = _VIDEO_INLINE_PATTERN.sub("", stripped).strip()
            if len(remaining) <= 3:
                continue
        line = _VIDEO_INLINE_PATTERN.sub("", line)
        clean_lines.append(line)

    text = _MULTI_BLANK_PATTERN.sub("\n\n", "\n".join(clean_lines))
    return text.strip()


def load_documents(knowledge_dir: Path) -> list[dict]:
    """加载所有 md 文件，清洗后返回 [{"path": str, "content": str, "category": str}, ...]"""
    docs = []
    for md_file in sorted(knowledge_dir.rglob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        cleaned = clean_markdown(content)
        if len(cleaned) < 100:  # 跳过内容太短的文档
            continue
        # 取相对路径（相对于知识库根目录）
        rel_path = md_file.relative_to(knowledge_dir)
        category = str(rel_path).split("/")[0] if "/" in str(rel_path) else str(rel_path.parent)
        docs.append({
            "path": str(rel_path).replace("\\", "/"),
            "content": cleaned,
            "category": category,
            "content_len": len(cleaned),
        })
    logger.info(f"已加载 {len(docs)} 篇有效文档")
    return docs


# ---------------------------------------------------------------------------
# LLM 调用
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """你是一个 RAG 系统评测数据生成专家。你的任务是阅读飞书（Feishu/Lark）帮助文档,
为知识库问答系统生成高质量的评测数据。

要求：
1. 生成的问题必须是飞书用户真实会问的问题（模拟客服场景）
2. 问题类型要多样化：操作步骤类、功能定义类、权限设置类、对比选择类、故障排查类
3. 答案必须严格基于提供的文档内容，不得编造
4. source_file 必须使用我提供的文件名，精确匹配

输出格式：严格 JSON 数组，每个元素包含：
{
  "question": "用户问题（中文，口语化，像真实用户在问客服）",
  "answer": "基于文档的标准答案（简洁完整，50-200字）",
  "source_file": "文档相对路径（必须与我提供的文件名完全一致）",
  "question_type": "操作步骤|功能定义|权限设置|对比选择|故障排查|用量限额"
}"""


def build_user_prompt(docs_batch: list[dict], batch_index: int, total_batches: int) -> str:
    """构建单批 LLM 调用的 user prompt"""
    parts = [
        f"以下是第 {batch_index + 1}/{total_batches} 批飞书帮助文档的内容。\n",
        "请基于这些文档生成 QA 评测数据。注意覆盖不同文档，避免集中在某一篇。\n",
    ]
    for i, doc in enumerate(docs_batch, 1):
        text = doc["content"]
        if len(text) > MAX_DOC_CHARS:
            text = text[:MAX_DOC_CHARS] + "\n\n... [文档过长，已截断]"
        parts.append(
            f"---\n"
            f"文档 {i}\n"
            f"文件名：{doc['path']}\n"
            f"分类：{doc['category']}\n"
            f"内容：\n{text}\n"
        )

    parts.append(
        f"\n请基于以上 {len(docs_batch)} 篇文档，生成 {QA_PER_BATCH} 个高质量的 QA 评测对。"
        f"请直接输出 JSON 数组，不要包含任何其他文字。"
    )
    return "\n".join(parts)


def call_llm(system: str, user: str) -> str:
    """调用 DeepSeek API"""
    if not API_KEY or "your-deepseek-key" in API_KEY:
        raise RuntimeError("请先在 .env 文件中配置有效的 DEEPSEEK_API_KEY")

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.4,
        max_tokens=4096,
    )
    content = resp.choices[0].message.content
    if not content:
        raise RuntimeError("API 返回空内容")
    return content


def parse_json_response(text: str) -> list[dict]:
    """从 LLM 回复中提取 JSON 数组"""
    text = text.strip()
    # 尝试去掉 markdown 代码块标记
    if text.startswith("```"):
        # 去掉开头的 ```json 或 ```
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "qa_pairs" in data:
            return data["qa_pairs"]
        elif isinstance(data, dict) and "items" in data:
            return data["items"]
        else:
            logger.warning(f"LLM 返回了非预期的 JSON 格式: {type(data)}")
            return []
    except json.JSONDecodeError as e:
        logger.error(f"JSON 解析失败: {e}")
        logger.debug(f"原始文本前 500 字符: {text[:500]}")
        # 尝试提取所有 JSON 对象
        objects = re.findall(r'\{[^{}]*"question"[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        if objects:
            logger.info(f"从文本中提取到 {len(objects)} 个 JSON 对象")
            results = []
            for obj_str in objects:
                try:
                    results.append(json.loads(obj_str))
                except json.JSONDecodeError:
                    continue
            return results
        return []


def validate_qa_pair(item: dict, valid_paths: set[str]) -> bool:
    """验证 QA 对是否完整、source_file 是否有效"""
    required = ["question", "answer", "source_file"]
    for key in required:
        if key not in item or not item[key]:
            return False
    if item["source_file"] not in valid_paths:
        logger.warning(f"source_file 不在文档列表中: {item['source_file']}")
        # 尝试模糊匹配
        matched = None
        for path in valid_paths:
            if path.endswith(item["source_file"]) or item["source_file"].endswith(path.rsplit("/", 1)[-1] if "/" in path else path):
                matched = path
                break
        if matched:
            item["source_file"] = matched
            logger.info(f"  已修正为: {matched}")
        else:
            logger.warning(f"  无法匹配，跳过此条")
            return False
    return True


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main():
    logger.info("=" * 60)
    logger.info("步骤 1/4: 加载 & 清洗文档")
    logger.info("=" * 60)

    docs = load_documents(KNOWLEDGE_DIR)
    all_paths = {d["path"] for d in docs}

    # -----------------------------------------------------------------------
    # 确保类别多样性：按分类分组，每类随机抽样
    # -----------------------------------------------------------------------
    logger.info("步骤 2/4: 跨类别抽样确保多样性")

    categories: dict[str, list[dict]] = {}
    for doc in docs:
        categories.setdefault(doc["category"], []).append(doc)

    logger.info(f"共 {len(categories)} 个类别: {list(categories.keys())}")

    num_batches = TOTAL_QA // QA_PER_BATCH  # 30/5 = 6 batches
    sampled_per_batch: list[list[dict]] = []

    # 将文档按类别洗牌，然后轮流分配
    cat_docs = list(categories.values())
    random.seed(42)
    for cat_docs_list in cat_docs:
        random.shuffle(cat_docs_list)

    # 每批从不同类别组中抽取文档
    cat_idx = 0
    doc_idx_in_cat = [0] * len(cat_docs)

    for batch_i in range(num_batches):
        batch_docs = []
        # 确保每批覆盖不同类别
        categories_used = set()
        attempts = 0
        while len(batch_docs) < FILES_PER_BATCH and attempts < 50:
            attempts += 1
            ci = cat_idx % len(cat_docs)
            cat = cat_docs[ci]
            di = doc_idx_in_cat[ci]

            if di < len(cat) and cat[ci % len(cat_docs)] is not None:
                # 实际取文档
                if di < len(cat):
                    doc = cat[di]
                    if doc["category"] not in categories_used or len(batch_docs) >= 3:
                        batch_docs.append(doc)
                        categories_used.add(doc["category"])
                        doc_idx_in_cat[ci] += 1
            cat_idx += 1

        sampled_per_batch.append(batch_docs)
        logger.info(
            f"  批次 {batch_i + 1}: "
            + ", ".join(f"{d['category'].split('/')[0][:8]}...({d['path'].split('/')[-1][:20]})" for d in batch_docs)
        )

    # -----------------------------------------------------------------------
    logger.info("步骤 3/4: 调用 LLM 生成 QA 对")
    logger.info("=" * 60)

    if not API_KEY or "your-deepseek-key" in API_KEY:
        logger.error("未配置有效的 DEEPSEEK_API_KEY！")
        logger.error("请编辑 .env 文件，将 DEEPSEEK_API_KEY 设置为你真实的 DeepSeek API Key")
        sys.exit(1)

    all_qa_pairs = []
    for batch_i, batch_docs in enumerate(sampled_per_batch):
        logger.info(f"正在生成第 {batch_i + 1}/{num_batches} 批...")

        # 避免重复使用同一文档生成过多问题
        batch_paths = {d["path"] for d in batch_docs}
        if batch_paths & {qa["source_file"] for qa in all_qa_pairs}:
            logger.info("  该批文档已有部分被使用过，正常")

        user_prompt = build_user_prompt(batch_docs, batch_i, num_batches)

        for retry in range(3):
            try:
                raw_response = call_llm(SYSTEM_PROMPT, user_prompt)
                pairs = parse_json_response(raw_response)
                if len(pairs) >= 3:  # 至少生成 3 条才算成功
                    break
                logger.warning(f"  仅解析出 {len(pairs)} 条，重试...")
            except Exception as e:
                logger.error(f"  API 调用失败 (尝试 {retry + 1}/3): {e}")
                if retry == 2:
                    logger.error("  该批次生成失败，跳过")
                    pairs = []
                    break

        valid_count = 0
        for pair in pairs:
            if validate_qa_pair(pair, all_paths):
                pair["id"] = len(all_qa_pairs) + 1
                # 从 source_file 提取分类
                src = pair.get("source_file", "")
                pair["category"] = src.split("/")[0] if "/" in src else "未知"
                all_qa_pairs.append(pair)
                valid_count += 1

        logger.info(f"  本批生成 {len(pairs)} 条，有效 {valid_count} 条，累计 {len(all_qa_pairs)} 条")

        # 如果已经够 30 条，停止
        if len(all_qa_pairs) >= TOTAL_QA:
            break

    # -----------------------------------------------------------------------
    logger.info("步骤 4/4: 保存结果")
    logger.info("=" * 60)

    # 截取恰好 30 条
    all_qa_pairs = all_qa_pairs[:TOTAL_QA]

    output = {
        "meta": {
            "total": len(all_qa_pairs),
            "description": "飞书知识库 RAG 评测数据集，由 LLM 自动生成",
            "generated_by": "generate_eval_dataset.py",
            "model": MODEL,
        },
        "data": all_qa_pairs,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"已保存 {len(all_qa_pairs)} 条评测数据到 {OUTPUT_FILE}")

    # 打印统计
    type_counts = {}
    cat_counts = {}
    for qa in all_qa_pairs:
        t = qa.get("question_type", "未分类")
        type_counts[t] = type_counts.get(t, 0) + 1
        cat_counts[qa.get("category", "未知")] = cat_counts.get(qa.get("category", "未知"), 0) + 1

    logger.info(f"问题类型分布: {type_counts}")
    logger.info(f"类别分布: {cat_counts}")


if __name__ == "__main__":
    main()
