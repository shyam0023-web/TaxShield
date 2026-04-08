import sqlite3
conn = sqlite3.connect('taxshield.db')
c = conn.cursor()
c.execute("UPDATE notices SET response_deadline = NULL WHERE response_deadline = ''")
conn.commit()
print(f"Fixed {c.rowcount} rows")
conn.close()
