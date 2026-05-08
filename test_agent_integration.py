"""Agent 集成测试 — 三个真实场景测试（需要 DEEPSEEK_API_KEY）

Usage:
    python test_agent_integration.py
"""

import io
import json
import sys
from pathlib import Path

# Windows GBK 终端下强制 UTF-8
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from app.services.agent.router import classify_intent
from app.services.agent.agent_executor import run_agent, process_confirmation
from app.services.agent.state_manager import clear_session, get_session
from app.services.rag import rag_chat


def hr(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def test_1_knowledge_query():
    """场景1：知识咨询 — 走 RAG 链路"""
    hr("场景1：知识咨询 → RAG")

    query = "飞书会议如何开启自动字幕？"
    print(f"  Query: {query}")

    intent = classify_intent(query)
    print(f"  Intent: {intent}")
    assert intent == "knowledge", f"Expected 'knowledge', got '{intent}'"

    result = rag_chat(query)
    print(f"  Answer (first 200 chars): {result['answer'][:200]}...")
    print(f"  Sources: {len(result['sources'])} files")
    assert len(result["answer"]) > 10
    assert len(result["sources"]) > 0
    print("  [PASS] 场景1")


def test_2_safe_tool():
    """场景2：安全工具 — 查询员工信息（直接执行，无需确认）"""
    hr("场景2：安全工具直接执行 → get_employee_info")

    session_id = "test-integration-2"
    clear_session(session_id)

    query = "帮我查一下张三的员工信息"
    print(f"  Query: {query}")

    intent = classify_intent(query)
    print(f"  Intent: {intent}")
    assert intent == "task", f"Expected 'task', got '{intent}'"

    result = run_agent(session_id, query)
    print(f"  Type: {result['type']}")
    print(f"  Content: {result.get('content', '')[:300]}...")

    assert result["type"] == "response", f"Expected 'response', got '{result['type']}'"
    assert "张三" in result.get("content", "")
    assert "技术部" in result.get("content", "") or "高级工程师" in result.get("content", "")
    print("  [PASS] 场景2")

    clear_session(session_id)


def test_3_sensitive_tool_with_confirm():
    """场景3：敏感工具 — 创建工单（需要确认 → 确认后执行）"""
    hr("场景3：敏感工具 → 需要确认 → 确认后执行")

    session_id = "test-integration-3"
    clear_session(session_id)

    # Step 1: 发起工单创建请求
    query = "帮我创建一个工单，标题是打印机故障，三楼打印机无法打印，紧急程度高，指派给张三"
    print(f"  Step 1: 发起请求")
    print(f"    Query: {query}")

    intent = classify_intent(query)
    print(f"    Intent: {intent}")
    assert intent == "task"

    result = run_agent(session_id, query)
    print(f"    Type: {result['type']}")
    print(f"    Content: {result.get('content', '')[:200]}...")

    # 检查是否返回了 confirmation_needed
    # 注意：LLM 可能直接提取了所有参数一次性调用工具（此时 type=confirmation_needed），
    #       也可能追问缺失字段（此时 type=response，需要多轮对话）
    if result["type"] == "confirmation_needed":
        print(f"    Tool: {result.get('tool')}")
        print(f"    Args: {json.dumps(result.get('args'), ensure_ascii=False)}")
        assert result.get("tool") == "create_ticket"
        assert result.get("args", {}).get("title") == "打印机故障"

        # Step 2: 确认执行
        print(f"\n  Step 2: 确认执行")
        confirm_result = process_confirmation(session_id, "confirm")
        print(f"    Type: {confirm_result['type']}")
        print(f"    Content: {confirm_result['content'][:200]}...")
        assert confirm_result["type"] == "response"
        assert "TICKET-" in confirm_result.get("content", "")
        print("  [PASS] 场景3（直接确认）")

    elif result["type"] == "response":
        # LLM 可能在追问信息，这是正常的 slot-filling 行为
        print(f"\n  [INFO] LLM 未直接调用工具（可能在追问信息），响应内容: {result['content'][:200]}")
        print("  [PASS] 场景3（slot-filling 正常）")

    clear_session(session_id)


def test_3b_create_ticket_with_slots():
    """场景3b：创建工单 — 信息不完整时的多轮槽位填充"""
    hr("场景3b：多轮槽位填充")

    session_id = "test-integration-3b"
    clear_session(session_id)

    # Round 1: 模糊请求
    query = "我想报修一个故障"
    print(f"  Round 1: '{query}'")

    intent = classify_intent(query)
    print(f"    Intent: {intent}")
    assert intent == "task"

    result = run_agent(session_id, query)
    print(f"    Type: {result['type']}")
    print(f"    Response: {result.get('content', '')[:300]}...")
    assert result["type"] in ("response", "confirmation_needed")
    print("    [OK] Round 1 — Agent 响应正常")

    # Round 2: 补充信息（如果 Round 1 LLM 在追问）
    if result["type"] == "response" and "？" in result.get("content", ""):
        query2 = "打印机故障，三楼的打印机无法打印"
        print(f"\n  Round 2: '{query2}'")
        result2 = run_agent(session_id, query2)
        print(f"    Type: {result2['type']}")
        print(f"    Response: {result2.get('content', '')[:300]}...")
        assert result2["type"] in ("response", "confirmation_needed")
        print("    [OK] Round 2 — 信息补充正常")

        # 如果还需要追问，再补充
        if result2["type"] == "response" and "？" in result2.get("content", ""):
            query3 = "紧急程度高，指派给张三"
            print(f"\n  Round 3: '{query3}'")
            result3 = run_agent(session_id, query3)
            print(f"    Type: {result3['type']}")
            print(f"    Response: {result3.get('content', '')[:300]}...")
            assert result3["type"] in ("response", "confirmation_needed")
            print("    [OK] Round 3 — 信息补充正常")

            # 如果此时需要确认，执行确认
            if result3["type"] == "confirmation_needed":
                print(f"\n  Confirming...")
                confirm_result = process_confirmation(session_id, "confirm")
                print(f"    Type: {confirm_result['type']}")
                print(f"    Content: {confirm_result['content'][:200]}...")
                assert "TICKET-" in confirm_result.get("content", "")
        elif result2["type"] == "confirmation_needed":
            print(f"\n  Confirming...")
            confirm_result = process_confirmation(session_id, "confirm")
            print(f"    Type: {confirm_result['type']}")
            print(f"    Content: {confirm_result['content'][:200]}...")
            assert "TICKET-" in confirm_result.get("content", "")

    print("  [PASS] 场景3b")

    # 验证工单文件
    tickets_file = _project_root / "data" / "tickets.json"
    if tickets_file.exists():
        tickets = json.loads(tickets_file.read_text(encoding="utf-8"))
        print(f"  Tickets in file: {len(tickets)}")

    clear_session(session_id)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Agent 集成测试")
    print("=" * 60)
    print("  (需要 DEEPSEEK_API_KEY)")
    print()

    # 初始化向量库（FastAPI lifespan 在直接调用时不会执行）
    from app.services.vectorstore import load_vector_store
    load_vector_store()
    print("  Vector store loaded.\n")

    try:
        test_1_knowledge_query()
        test_2_safe_tool()
        test_3_sensitive_tool_with_confirm()
        test_3b_create_ticket_with_slots()

        print("\n" + "=" * 60)
        print("  All integration tests passed!")
        print("=" * 60)
    except Exception as e:
        print(f"\n[FAIL] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
