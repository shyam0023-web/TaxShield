import sqlite3
conn = sqlite3.connect('taxshield.db')
c = conn.cursor()
c.execute("SELECT error_message FROM notices WHERE id IN ('1b277349-81e2-4c88-ad09-329b74da0043', '6ca3cec3-8fff-45ff-ac85-6110f3ba29f5')")
for row in c.fetchall():
    print(repr(row[0]))
conn.close()
