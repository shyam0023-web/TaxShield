import sqlite3

conn = sqlite3.connect('taxshield.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT id, processing_status FROM notices ORDER BY created_at DESC LIMIT 3")
for row in c.fetchall():
    print(f"Notice ID: {row['id']} - status: {row['processing_status']}")
conn.close()
