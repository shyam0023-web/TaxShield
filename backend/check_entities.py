import sqlite3
import json

conn = sqlite3.connect('taxshield.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT id, entities, notice_annotations FROM notices ORDER BY created_at DESC LIMIT 3")
for row in c.fetchall():
    print(f"Notice ID: {row['id']}")
    print(f"Entities: {row['entities']}")
    print("-" * 40)
conn.close()
