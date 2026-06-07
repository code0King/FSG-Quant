"""检查数据库状态"""
import sqlite3
conn = sqlite3.connect("data/raw/financial_data.sqlite")
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
print("Tables:", tables)
for t in tables:
    c.execute(f'SELECT COUNT(*) FROM "{t}"')
    print(f"  {t}: {c.fetchone()[0]} rows")
    c.execute(f'SELECT * FROM "{t}" LIMIT 2')
    print(f"    cols: {[d[0] for d in c.description]}")
    rows = c.fetchall()
    for row in rows:
        print(f"    {row}")
conn.close()
