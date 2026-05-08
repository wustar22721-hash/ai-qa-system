"""Agent module test script — verify tool calls, state management, intent routing

Usage:
    python test_agent.py
"""

import json
import sys
from pathlib import Path

# Ensure project root is in sys.path
_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def green(s):
    return s  # keep it simple, avoid ANSI codes on Windows


# ──────────────────────────────────────────────
# Test 1: Tool functions (no API key needed)
# ──────────────────────────────────────────────

def test_tools():
    print("=" * 60)
    print("Test 1: Tool functions")
    print("=" * 60)

    from app.services.agent.tools import get_employee_info, create_ticket, send_notification

    # 1.1 Employee lookup — found
    result = get_employee_info(u'张三')
    assert result["found"] is True
    assert result["department"] == u'技术部'
    print(f"  [OK] get_employee_info('Zhang San') -> {result['name']} / {result['department']} / {result['position']}")

    # 1.2 Employee lookup — not found
    result = get_employee_info(u'路人甲')
    assert result["found"] is False
    print(f"  [OK] get_employee_info('Stranger') -> {result['message']}")

    # 1.3 Create ticket (MySQL)
    ticket_id = create_ticket(u'打印机故障', u'三楼打印机无法打印', u'张三', u'高')
    assert ticket_id.startswith(u'工单创建成功')
    assert "TICKET-" in ticket_id
    print(f"  [OK] create_ticket -> {ticket_id}")

    # Verify ticket in MySQL
    import pymysql
    conn = pymysql.connect(host="127.0.0.1", port=3306, user="root", password="123456", database="agent_db", charset="utf8mb4")
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM tickets")
        count = cur.fetchone()[0]
        assert count >= 1
        print(f"  [OK] Tickets in MySQL: {count} rows")
    conn.close()

    # 1.4 Send notification
    result = send_notification("Li Si", "Your ticket TK-001 has been processed")
    assert result is True
    print(f"  [OK] send_notification -> {result}")

    print("  Test 1 passed\n")


# ──────────────────────────────────────────────
# Test 2: State management
# ──────────────────────────────────────────────

def test_state_manager():
    print("=" * 60)
    print("Test 2: State management")
    print("=" * 60)

    from app.services.agent.state_manager import (
        get_session, update_session, clear_session,
        add_message, get_history,
        set_pending_action, get_pending_action, clear_pending_action,
    )

    sid = "test-session-001"

    # 2.1 Create session
    session = get_session(sid)
    assert session["history"] == []
    assert session["collected_info"] == {}
    assert session["pending_action"] is None
    print("  [OK] get_session creates default state")

    # 2.2 Update collected_info (cumulative)
    update_session(sid, collected_info={"title": "Printer issue"})
    update_session(sid, collected_info={"description": "Cannot print"})
    session = get_session(sid)
    assert session["collected_info"] == {"title": "Printer issue", "description": "Cannot print"}
    print("  [OK] update_session accumulates collected_info")

    # 2.3 Add messages
    add_message(sid, "user", "Help me create a ticket")
    add_message(sid, "assistant", "Sure, what is the title?")
    history = get_history(sid)
    assert len(history) == 2
    print(f"  [OK] add_message / get_history ({len(history)} messages)")

    # 2.4 Pending action
    set_pending_action(sid, "create_ticket", {"title": "Test", "description": "Desc", "assignee": "Wang Wu", "priority": "medium"})
    pending = get_pending_action(sid)
    assert pending["tool"] == "create_ticket"
    print(f"  [OK] set_pending_action / get_pending_action -> {pending['tool']}")

    # 2.5 Clear pending
    clear_pending_action(sid)
    assert get_pending_action(sid) is None
    print("  [OK] clear_pending_action")

    # 2.6 Clear session
    clear_session(sid)
    new_s = get_session(sid)
    assert new_s["history"] == []
    print("  [OK] clear_session -> new empty session")

    print("  Test 2 passed\n")


# ──────────────────────────────────────────────
# Test 3: Intent routing (keyword match)
# ──────────────────────────────────────────────

def test_router_keywords():
    print("=" * 60)
    print("Test 3: Intent routing (keyword match)")
    print("=" * 60)

    from app.services.agent.router import _quick_classify

    # Task keywords
    assert _quick_classify(u'帮我创建一个工单') == "task"
    print("  [OK] 'Help me create a ticket' -> task")

    assert _quick_classify(u'查询员工张三的信息') == "task"
    print("  [OK] 'Query employee Zhang San info' -> task")

    assert _quick_classify(u'给李四发送通知') == "task"
    print("  [OK] 'Send notification to Li Si' -> task")

    assert _quick_classify(u'打印机故障报修') == "task"
    print("  [OK] 'Printer fault repair' -> task")

    # Knowledge keywords
    assert _quick_classify(u'飞书会议怎么开启字幕') == "knowledge"
    print("  [OK] 'How to enable subtitles in Feishu meeting' -> knowledge")

    assert _quick_classify(u'如何设置考勤规则') == "knowledge"
    print("  [OK] 'How to set attendance rules' -> knowledge")

    # Ambiguous case
    result = _quick_classify(u'今天天气不错')
    assert result is None
    print("  [OK] 'Nice weather today' -> None (needs LLM)")

    print("  Test 3 passed\n")


# ──────────────────────────────────────────────
# Test 4: Tool definitions integrity
# ──────────────────────────────────────────────

def test_tool_definitions():
    print("=" * 60)
    print("Test 4: Tool definitions integrity")
    print("=" * 60)

    from app.services.agent.tools import TOOL_DEFINITIONS, TOOL_EXECUTORS, SENSITIVE_TOOLS

    tool_names = {t["function"]["name"] for t in TOOL_DEFINITIONS}

    assert len(TOOL_DEFINITIONS) == 3
    print(f"  [OK] {len(TOOL_DEFINITIONS)} tools defined")

    assert tool_names == {"get_employee_info", "create_ticket", "send_notification"}
    print(f"  [OK] Tool names: {tool_names}")

    assert TOOL_EXECUTORS.keys() == tool_names
    print("  [OK] Every tool has an executor")

    assert SENSITIVE_TOOLS == {"create_ticket", "send_notification"}
    print(f"  [OK] Sensitive tools: {SENSITIVE_TOOLS}")

    for t in TOOL_DEFINITIONS:
        assert t["type"] == "function"
        assert "name" in t["function"]
        assert "parameters" in t["function"]
        assert "required" in t["function"]["parameters"]
    print("  [OK] All tool definitions match OpenAI function calling format")

    print("  Test 4 passed\n")


# ──────────────────────────────────────────────
# Test 5: Agent response structure
# ──────────────────────────────────────────────

def test_agent_response_structure():
    print("=" * 60)
    print("Test 5: Agent response structure (no API key)")
    print("=" * 60)

    import app.core.config as config_module
    import app.services.agent.agent_executor as agent_exec
    from app.services.agent.state_manager import clear_session

    sid = "test-agent-struct"
    clear_session(sid)

    key_backup = config_module.DEEPSEEK_API_KEY
    config_module.DEEPSEEK_API_KEY = ""
    agent_exec.DEEPSEEK_API_KEY = ""

    result = agent_exec.run_agent(sid, "Help me create a ticket")
    assert result["type"] == "error"
    assert "DEEPSEEK_API_KEY" in result["content"]
    print(f"  [OK] No API key -> error: {result['content'][:50]}...")

    config_module.DEEPSEEK_API_KEY = key_backup
    agent_exec.DEEPSEEK_API_KEY = key_backup
    clear_session(sid)
    print("  Test 5 passed\n")


# ──────────────────────────────────────────────
# Test 6: Confirmation flow (state only)
# ──────────────────────────────────────────────

def test_confirmation_flow():
    print("=" * 60)
    print("Test 6: Confirmation flow (state management)")
    print("=" * 60)

    from app.services.agent.state_manager import (
        get_session, set_pending_action, get_pending_action,
        clear_pending_action, clear_session,
    )
    from app.services.agent.tools import send_notification

    sid = "test-confirm"
    clear_session(sid)

    set_pending_action(sid, "create_ticket", {
        "title": "Network issue",
        "description": "WiFi not connecting",
        "assignee": "Wang Wu",
        "priority": "high",
    })

    pending = get_pending_action(sid)
    assert pending is not None
    assert pending["tool"] == "create_ticket"
    print(f"  [OK] Pending action set: {pending['tool']}")

    # Cancel
    clear_pending_action(sid)
    assert get_pending_action(sid) is None
    print("  [OK] Pending action cancelled")

    # Confirm + execute
    set_pending_action(sid, "send_notification", {"user": "Zhang San", "message": "Meeting cancelled"})
    pending = get_pending_action(sid)
    result = send_notification(**pending["args"])
    assert result is True
    clear_pending_action(sid)
    print(f"  [OK] Confirmed and executed send_notification -> {result}")

    clear_session(sid)
    print("  Test 6 passed\n")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

if __name__ == "__main__":
    print("\n=== Agent Module Tests ===\n")

    try:
        test_tools()
        test_state_manager()
        test_router_keywords()
        test_tool_definitions()
        test_agent_response_structure()
        test_confirmation_flow()

        print("=" * 60)
        print("[OK] All tests passed!")
        print("=" * 60)
        print("\nNote: Test 3 (LLM classification) and full agent_executor integration test require DEEPSEEK_API_KEY.")
    except AssertionError as e:
        print(f"\n[FAIL] Test assertion failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Runtime error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
