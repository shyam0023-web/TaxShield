import sqlite3
conn = sqlite3.connect("taxshield.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT id, status, draft_status, error_message FROM notices ORDER BY created_at DESC LIMIT 3")
for r in c.fetchall():
    print(f"ID: {r['id']}")
    print(f"  status: {r['status']}")
    print(f"  draft_status: {r['draft_status']}")
    print(f"  error: {r['error_message']}")
    print()
conn.close()
