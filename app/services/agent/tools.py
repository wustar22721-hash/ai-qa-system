"""Agent 工具定义 — MySQL 实现"""

import json
import logging
import os

logger = logging.getLogger(__name__)


def _get_db_connection():
    """获取 MySQL 连接（延迟导入 pymysql）"""
    import pymysql
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", "123456"),
        database="agent_db",
        charset="utf8mb4",
    )


# ═══════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════

def get_employee_info(name: str) -> dict:
    """从 MySQL 查询员工信息（含直属上级）"""
    conn = _get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    e.id, e.name, e.department, e.position,
                    e.email, e.phone,
                    l.name AS leader_name,
                    l.position AS leader_position
                FROM employees e
                LEFT JOIN employees l ON e.leader_id = l.id
                WHERE e.name = %s
                """,
                (name,),
            )
            row = cur.fetchone()
            if row:
                return {
                    "found": True,
                    "id": row[0],
                    "name": row[1],
                    "department": row[2],
                    "position": row[3],
                    "email": row[4],
                    "phone": row[5],
                    "leader_name": row[6],
                    "leader_position": row[7],
                }
            return {"found": False, "name": name, "message": f"未找到员工「{name}」的信息"}
    finally:
        conn.close()


def create_ticket(title: str, description: str, assignee: str, priority: str) -> str:
    """创建工单，写入 MySQL tickets 表"""
    conn = _get_db_connection()
    try:
        with conn.cursor() as cur:
            # 查找指派员工 ID
            cur.execute("SELECT id FROM employees WHERE name = %s", (assignee,))
            row = cur.fetchone()
            if not row:
                return f"错误：未找到员工「{assignee}」，工单创建失败"

            assignee_id = row[0]

            # 生成工单编号
            cur.execute("SELECT COUNT(*) FROM tickets")
            count = cur.fetchone()[0]
            ticket_id = f"TICKET-{count + 1:03d}"

            # 映射优先级
            priority_map = {"低": "low", "中": "medium", "高": "high", "紧急": "urgent"}
            db_priority = priority_map.get(priority, "medium")

            cur.execute(
                """INSERT INTO tickets (ticket_id, title, description, assignee_id, priority, status)
                   VALUES (%s, %s, %s, %s, %s, 'open')""",
                (ticket_id, title, description, assignee_id, db_priority),
            )
            conn.commit()

            logger.info("工单已创建: %s → MySQL", ticket_id)
            return f"工单创建成功！工单号：{ticket_id}，状态：open，指派给：{assignee}"
    finally:
        conn.close()


def send_notification(user: str, message: str) -> bool:
    """发送通知（mock：打印日志）"""
    logger.info("[通知] 发送给: %s | 内容: %s", user, message)
    print(f"\n{'='*50}")
    print(f"[Mock Notification]")
    print(f"   To: {user}")
    print(f"   Message: {message}")
    print(f"{'='*50}\n")
    return True


# ═══════════════════════════════════════════════════════════════
# OpenAI function calling 工具定义
# ═══════════════════════════════════════════════════════════════

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_employee_info",
            "description": "根据员工姓名查询其部门、职位、联系方式等信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "员工姓名"}
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "创建工单。执行前必须向用户确认标题、描述、紧急程度和指派对象。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "工单标题"},
                    "description": {"type": "string", "description": "故障/问题描述"},
                    "assignee": {"type": "string", "description": "指派对象姓名"},
                    "priority": {"type": "string", "enum": ["低", "中", "高", "紧急"], "description": "紧急程度"},
                },
                "required": ["title", "description", "assignee", "priority"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_notification",
            "description": "向指定用户发送通知消息。执行前必须向用户确认收件人和消息内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "user": {"type": "string", "description": "收件人姓名或标识"},
                    "message": {"type": "string", "description": "通知消息内容"},
                },
                "required": ["user", "message"],
            },
        },
    },
]

SENSITIVE_TOOLS = {"create_ticket", "send_notification"}

TOOL_EXECUTORS = {
    "get_employee_info": get_employee_info,
    "create_ticket": create_ticket,
    "send_notification": send_notification,
}
