import sqlite3
conn = sqlite3.connect('taxshield.db')
c = conn.cursor()

print("=== USERS ===")
c.execute("SELECT id, email FROM users")
for row in c.fetchall():
    print(row)

print("\n=== NOTICES (user_id) ===")
c.execute("SELECT id, user_id, status, draft_status FROM notices ORDER BY created_at DESC")
for row in c.fetchall():
    print(row)

conn.close()
