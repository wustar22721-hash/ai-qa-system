"""
RAG 检索质量评测脚本

遍历 eval_dataset.json 的每个问题，分别用两种策略检索：
  策略 A：纯向量检索（Vector Search）
  策略 B：向量检索 + 混合 Reranker

评测指标：Hit@1, Hit@3, MRR
结果输出：终端 Markdown 表格 + 写入 eval_results.md

用法：
    python run_evaluation.py
"""

import json
import logging
import sys
import time
from pathlib import Path

# 确保项目根在 sys.path
_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 初始化向量库（复用 main.py 的逻辑，但不启动 FastAPI）
# ---------------------------------------------------------------------------
import chromadb
from app.core.config import CHROMA_PERSIST_DIR
from app.services.vectorstore import similarity_search_with_score, load_vector_store
from app.services.reranker import rerank


def init_vector_store() -> None:
    """加载已有向量库，如不存在则报错退出"""
    persist_path = Path(CHROMA_PERSIST_DIR)
    if not persist_path.is_dir():
        logger.error(f"ChromaDB 数据目录不存在: {CHROMA_PERSIST_DIR}")
        logger.error("请先运行 python app/main.py 构建向量库")
        sys.exit(1)

    try:
        client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        col = client.get_collection("langchain")
        count = col.count()
        if count == 0:
            logger.error("向量库为空，请先运行 python app/main.py 构建向量库")
            sys.exit(1)
        logger.info(f"向量库已加载，共 {count} 条记录")
        load_vector_store()
    except Exception as e:
        logger.error(f"加载向量库失败: {e}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# 评测核心
# ---------------------------------------------------------------------------
def get_filename(source_file: str) -> str:
    """从完整相对路径中提取文件名"""
    return Path(source_file).name


def evaluate_strategy_a(query: str, expected_file: str, top_k: int = 10) -> dict:
    """策略 A：纯向量检索，返回 rank（从 1 开始，0 表示未命中）"""
    try:
        results = similarity_search_with_score(query, top_k=top_k)
    except Exception as e:
        logger.warning(f"向量检索失败: {e}")
        return {"rank": 0, "results": [], "error": str(e)}

    expected_name = get_filename(expected_file)
    rank = 0
    for i, r in enumerate(results):
        src = r.get("source", "")
        if get_filename(src) == expected_name:
            rank = i + 1
            break

    return {"rank": rank, "results": results, "error": None}


def evaluate_strategy_b(query: str, expected_file: str, search_k: int = 10, final_k: int = 5) -> dict:
    """策略 B：向量检索 10 → Reranker 排序 5，返回 rank（从 1 开始，0 表示未命中）"""
    try:
        candidates = similarity_search_with_score(query, top_k=search_k)
    except Exception as e:
        logger.warning(f"向量检索失败: {e}")
        return {"rank": 0, "results": [], "error": str(e)}

    try:
        reranked = rerank(query, candidates, top_k=final_k)
    except Exception as e:
        logger.warning(f"Reranker 失败，回退到向量结果: {e}")
        # 回退：直接用向量结果的前 N 条
        reranked = [{"content": r["content"], "source": r["source"]} for r in candidates[:final_k]]

    expected_name = get_filename(expected_file)
    rank = 0
    for i, r in enumerate(reranked):
        src = r.get("source", "")
        if get_filename(src) == expected_name:
            rank = i + 1
            break

    return {
        "rank": rank,
        "results": reranked,
        "candidates_retrieved": len(candidates),
        "error": None,
    }


def compute_metrics(items: list[dict]) -> dict:
    """给定 rank 值列表，计算 Hit@1, Hit@3, MRR"""
    total = len(items)
    if total == 0:
        return {"total": 0, "hit_at_1": 0, "hit_at_3": 0, "mrr": 0}

    hit1 = sum(1 for it in items if it["rank"] == 1)
    hit3 = sum(1 for it in items if 1 <= it["rank"] <= 3)
    mrr = sum(1.0 / it["rank"] for it in items if it["rank"] >= 1) / total

    return {
        "total": total,
        "hit_at_1": round(hit1 / total, 4),
        "hit_at_3": round(hit3 / total, 4),
        "mrr": round(mrr, 4),
    }


# ---------------------------------------------------------------------------
# Markdown 表格输出
# ---------------------------------------------------------------------------
def render_comparison_table(
    metrics_a: dict, metrics_b: dict, errors: list[dict]
) -> str:
    """生成策略 A vs B 对比 Markdown 表格"""
    lines = [
        "## RAG 检索评测结果",
        "",
        f"**评测数据集**：eval_dataset.json（共 {metrics_a['total']} 条）",
        "",
        "### 策略对比",
        "",
        "| 指标 | 策略 A（纯向量检索） | 策略 B（向量 + Reranker） | 提升 |",
        "|------|----------------------|---------------------------|------|",
    ]

    for key, label in [("hit_at_1", "Hit@1"), ("hit_at_3", "Hit@3"), ("mrr", "MRR")]:
        a = metrics_a[key]
        b = metrics_b[key]
        diff = round(b - a, 4)
        sign = "+" if diff > 0 else ""
        diff_str = f"{sign}{diff:.2%}" if key != "mrr" else f"{sign}{diff:.4f}"
        lines.append(f"| {label} | {a:.2%} | {b:.2%} | {diff_str} |")

    # 错误统计
    lines.append("")
    lines.append("### 错误记录")
    if errors:
        lines.append("")
        for err in errors:
            lines.append(f"- [{err['id']}] **{err['question'][:60]}...** → `{str(err['error'])[:200]}`")
    else:
        lines.append("无错误，所有评测项均成功完成。")

    return "\n".join(lines)


def render_detail_table(items_a: list[dict], items_b: list[dict], eval_data: list[dict]) -> str:
    """逐条明细 Markdown 表格"""
    table = [
        "",
        "### 逐条明细",
        "",
        "| ID | 问题 | 策略 A Rank | 策略 B Rank | 最佳 |",
        "|----|------|------------|------------|------|",
    ]
    for i, (a, b, qa) in enumerate(zip(items_a, items_b, eval_data)):
        q = qa.get("question", "")[:50]
        rank_a = a["rank"]
        rank_b = b["rank"]
        best = "A=B"
        if rank_a and rank_b:
            if rank_a < rank_b:
                best = "A 更优"
            elif rank_b < rank_a:
                best = "B 更优"
        elif rank_a and not rank_b:
            best = "A 命中"
        elif rank_b and not rank_a:
            best = "B 命中"
        else:
            best = "均未命中"

        rank_a_str = str(rank_a) if rank_a else "-"
        rank_b_str = str(rank_b) if rank_b else "-"
        table.append(f"| {qa['id']} | {q}... | {rank_a_str} | {rank_b_str} | {best} |")

    return "\n".join(table)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main():
    # ── 1. 加载数据集 ──────────────────────────────────────────
    dataset_path = _project_root / "eval_dataset.json"
    if not dataset_path.exists():
        logger.error(f"数据集文件不存在: {dataset_path}")
        logger.error("请先运行 generate_eval_dataset.py 生成评测数据")
        sys.exit(1)

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    eval_data = dataset.get("data", [])
    logger.info(f"已加载 {len(eval_data)} 条评测数据")

    # ── 2. 初始化向量库 ──────────────────────────────────────
    init_vector_store()

    # ── 3. 逐条评测 ──────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("开始评测...")
    logger.info("=" * 60)

    items_a: list[dict] = []  # [{id, rank, question}]
    items_b: list[dict] = []
    errors: list[dict] = []

    for idx, qa in enumerate(eval_data):
        question = qa.get("question", "")
        source_file = qa.get("source_file", "")
        qa_id = qa.get("id", idx + 1)

        if not question or not source_file:
            logger.warning(f"[{qa_id}] 跳过：缺少 question 或 source_file")
            continue

        logger.info(f"[{qa_id}/{len(eval_data)}] {question[:60]}...")

        # 策略 A
        result_a = evaluate_strategy_a(question, source_file, top_k=10)
        result_a["id"] = qa_id
        result_a["question"] = question
        items_a.append(result_a)

        # 策略 B
        result_b = evaluate_strategy_b(question, source_file, search_k=10, final_k=5)
        result_b["id"] = qa_id
        result_b["question"] = question
        items_b.append(result_b)

        # 收集错误
        if result_a.get("error"):
            errors.append(result_a)
        if result_b.get("error"):
            errors.append(result_b)

        # 避免 API 限流
        time.sleep(0.1)

    # ── 4. 计算指标 ──────────────────────────────────────────
    metrics_a = compute_metrics(items_a)
    metrics_b = compute_metrics(items_b)

    logger.info("=" * 60)
    logger.info("评测完成")
    logger.info(f"  策略 A — Hit@1: {metrics_a['hit_at_1']:.2%}, "
                f"Hit@3: {metrics_a['hit_at_3']:.2%}, MRR: {metrics_a['mrr']:.4f}")
    logger.info(f"  策略 B — Hit@1: {metrics_b['hit_at_1']:.2%}, "
                f"Hit@3: {metrics_b['hit_at_3']:.2%}, MRR: {metrics_b['mrr']:.4f}")

    # ── 5. 生成报告 ──────────────────────────────────────────
    table = render_comparison_table(metrics_a, metrics_b, errors)
    detail = render_detail_table(items_a, items_b, eval_data)

    # 终端输出
    print("\n" + "=" * 60)
    print(table)
    print(detail)

    # 写入文件
    report_path = _project_root / "eval_results.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(table + "\n" + detail + "\n")

    logger.info(f"详细结果已保存至 {report_path}")


if __name__ == "__main__":
    main()
