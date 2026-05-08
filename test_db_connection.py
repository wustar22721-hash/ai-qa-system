"""MySQL 连接验证脚本 — 测试员工查询和工单操作

前置条件：
    1. 已安装 MySQL，并执行 scripts/init_db.sql
    2. pip install pymysql

配置：
    直接修改下方 DB_CONFIG 或通过环境变量设置
"""

import os

# 数据库连接配置（按你的实际环境修改）
DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": "agent_db",
    "charset": "utf8mb4",
}


def get_connection():
    """获取数据库连接"""
    import pymysql
    return pymysql.connect(**DB_CONFIG)


# ──────────────────────────────────────────────
# 测试 1: 基础连接
# ──────────────────────────────────────────────

def test_connection():
    print("=" * 50)
    print("Test 1: Connection")
    print("=" * 50)
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION()")
            version = cur.fetchone()
            print(f"  [OK] MySQL version: {version[0]}")
        conn.close()
        print("  [OK] Connection OK\n")
    except Exception as e:
        print(f"  [FAIL] {e}\n")
        raise


# ──────────────────────────────────────────────
# 测试 2: 查询员工信息
# ──────────────────────────────────────────────

def test_get_employee():
    print("=" * 50)
    print("Test 2: Get employee info")
    print("=" * 50)

    test_cases = ["张三", "李雪", "路人甲"]

    for name in test_cases:
        result = get_employee_info(name)
        if result["found"]:
            print(f"  [OK] {name} -> {result['department']} / {result['position']} / {result['email']}")
            if result.get("leader_name"):
                print(f"       上级: {result['leader_name']} ({result.get('leader_position', '')})")
        else:
            print(f"  [OK] {name} -> {result['message']}")
    print()


def get_employee_info(name: str) -> dict:
    """从 MySQL 查询员工信息（含上级信息）"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    e.id,
                    e.name,
                    e.department,
                    e.position,
                    e.email,
                    e.phone,
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


# ──────────────────────────────────────────────
# 测试 3: 按部门查询
# ──────────────────────────────────────────────

def test_list_by_department():
    print("=" * 50)
    print("Test 3: List by department")
    print("=" * 50)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT department, COUNT(*) AS cnt
                FROM employees
                GROUP BY department
                ORDER BY cnt DESC
                """
            )
            for dept, cnt in cur.fetchall():
                print(f"  {dept}: {cnt} 人")
    finally:
        conn.close()
    print("  [OK]\n")


# ──────────────────────────────────────────────
# 测试 4: 创建工单
# ──────────────────────────────────────────────

def test_create_ticket():
    print("=" * 50)
    print("Test 4: Create ticket")
    print("=" * 50)

    result = create_ticket(
        title="测试工单",
        description="这是通过 Python 脚本创建的测试工单",
        assignee_name="张三",
        priority="medium",
    )
    print(f"  [OK] {result}\n")


def create_ticket(title: str, description: str, assignee_name: str, priority: str) -> str:
    """创建工单，写入 MySQL"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 查找指派员工
            cur.execute("SELECT id FROM employees WHERE name = %s", (assignee_name,))
            row = cur.fetchone()
            if not row:
                return f"错误：未找到员工「{assignee_name}」"

            assignee_id = row[0]

            # 生成工单编号
            cur.execute("SELECT COUNT(*) FROM tickets")
            count = cur.fetchone()[0]
            ticket_id = f"TICKET-{count + 1:03d}"

            # 映射 priority
            priority_map = {"低": "low", "中": "medium", "高": "high", "紧急": "urgent"}
            db_priority = priority_map.get(priority, "medium")

            cur.execute(
                """INSERT INTO tickets (ticket_id, title, description, assignee_id, priority, status)
                   VALUES (%s, %s, %s, %s, %s, 'open')""",
                (ticket_id, title, description, assignee_id, db_priority),
            )
            conn.commit()

            return f"工单创建成功！工单号：{ticket_id}，状态：open，指派给：{assignee_name}"
    finally:
        conn.close()


# ──────────────────────────────────────────────
# 测试 5: 模糊搜索
# ──────────────────────────────────────────────

def test_fuzzy_search():
    print("=" * 50)
    print("Test 5: Fuzzy search")
    print("=" * 50)

    keyword = "张"
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT name, department, position FROM employees WHERE name LIKE %s",
                (f"%{keyword}%",),
            )
            rows = cur.fetchall()
            print(f"  Search '{keyword}' -> {len(rows)} result(s):")
            for r in rows:
                print(f"    {r[0]} / {r[1]} / {r[2]}")
    finally:
        conn.close()
    print("  [OK]\n")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

if __name__ == "__main__":
    print("\n=== MySQL Connection Test ===\n")

    try:
        import pymysql
    except ImportError:
        print("[FAIL] pymysql not installed. Run: pip install pymysql")
        exit(1)

    try:
        test_connection()
        test_get_employee()
        test_list_by_department()
        test_create_ticket()
        test_fuzzy_search()

        print("=" * 50)
        print("[OK] All tests passed!")
        print("=" * 50)
    except Exception as e:
        print(f"\n[FAIL] {e}")
        import traceback
        traceback.print_exc()
        exit(1)
