import sqlite3
conn = sqlite3.connect('taxshield.db')
c = conn.cursor()
c.execute("SELECT id, response_deadline FROM notices")
for row in c.fetchall():
    print(repr(row))
conn.close()
