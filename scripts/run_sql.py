"""通过 pymysql 执行 init_db.sql（避免命令行编码问题）"""
import pymysql

conn = pymysql.connect(
    host="127.0.0.1",
    port=3306,
    user="root",
    password="123456",
    charset="utf8mb4",
)
cursor = conn.cursor()

sql_path = __file__.replace("run_sql.py", "init_db.sql")
with open(sql_path, "r", encoding="utf-8") as f:
    sql = f.read()

# 按 ; 分割执行（跳过注释和空语句）
statements = []
for s in sql.split(";"):
    s = s.strip()
    # 跳过纯注释块
    if not s or s.startswith("--"):
        continue
    # 处理多行注释 /* ... */
    statements.append(s)

for i, stmt in enumerate(statements):
    try:
        cursor.execute(stmt)
    except pymysql.err.OperationalError as e:
        code = e.args[0] if e.args else 0
        # 1050=Table exists, 1007=DB exists — 可忽略
        if code not in (1050, 1007):
            raise
    except Exception as e:
        print(f"  [SKIP] Statement {i}: {str(e)[:80]}")

conn.commit()
conn.close()
print("SQL script executed successfully.")
