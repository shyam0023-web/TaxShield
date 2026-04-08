import sqlite3
conn = sqlite3.connect("taxshield.db")
c = conn.cursor()
c.execute("SELECT id, case_id, status, draft_status, error_message, length(draft_reply) FROM notices ORDER BY created_at DESC LIMIT 6")
for r in c.fetchall():
    print(r)
conn.close()
