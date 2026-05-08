"""tools.py 迁移至 MySQL 的参考实现

将 tools.py 中以下三处替换为 MySQL 版本：
    1. get_employee_info   → 从 MySQL 查询（含上级信息）
    2. create_ticket       → 写入 MySQL tickets 表
    3. _MOCK_EMPLOYEES     → 删除硬编码字典

迁移步骤：
    1. pip install pymysql
    2. mysql -u root -p < scripts/init_db.sql
    3. 将本文件中的函数覆盖到 tools.py 对应位置
    4. 在 .env 中添加 MYSQL_HOST / MYSQL_PORT / MYSQL_USER / MYSQL_PASSWORD
"""

import json
import logging
import os

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# 数据库连接（tools.py 顶部新增）
# ═══════════════════════════════════════════════════════════════

def _get_db_connection():
    """获取 MySQL 连接。延迟导入 pymysql，避免未安装时阻塞整个模块加载。"""
    import pymysql
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database="agent_db",
        charset="utf8mb4",
    )


# ═══════════════════════════════════════════════════════════════
# 删除原来的 _MOCK_EMPLOYEES 字典和旧的 get_employee_info
# 替换为以下版本
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


# ═══════════════════════════════════════════════════════════════
# 删除旧的 create_ticket（JSON 文件版本）
# 替换为以下版本
# ═══════════════════════════════════════════════════════════════

def create_ticket(title: str, description: str, assignee: str, priority: str) -> str:
    """创建工单，写入 MySQL tickets 表"""
    conn = _get_db_connection()
    try:
        with conn.cursor() as cur:
            # 1. 查找指派员工 ID
            cur.execute("SELECT id FROM employees WHERE name = %s", (assignee,))
            row = cur.fetchone()
            if not row:
                return f"错误：未找到员工「{assignee}」，工单创建失败"

            assignee_id = row[0]

            # 2. 生成工单编号
            cur.execute("SELECT COUNT(*) FROM tickets")
            count = cur.fetchone()[0]
            ticket_id = f"TICKET-{count + 1:03d}"

            # 3. 映射优先级
            priority_map = {"低": "low", "中": "medium", "高": "high", "紧急": "urgent"}
            db_priority = priority_map.get(priority, "medium")

            # 4. 插入工单
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


# ═══════════════════════════════════════════════════════════════
# send_notification 保持不变（mock）
# ═══════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════
# 可选：工具箱扩展 — 模糊搜索、按部门查询
# ═══════════════════════════════════════════════════════════════

def search_employees(keyword: str) -> list[dict]:
    """按姓名模糊搜索员工"""
    conn = _get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT name, department, position, email FROM employees WHERE name LIKE %s",
                (f"%{keyword}%",),
            )
            return [
                {"name": r[0], "department": r[1], "position": r[2], "email": r[3]}
                for r in cur.fetchall()
            ]
    finally:
        conn.close()


def list_employees_by_department(department: str) -> list[dict]:
    """按部门列出员工"""
    conn = _get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT name, position, email FROM employees WHERE department = %s",
                (department,),
            )
            return [
                {"name": r[0], "position": r[1], "email": r[2]}
                for r in cur.fetchall()
            ]
    finally:
        conn.close()
