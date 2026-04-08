import sqlite3
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
new_hash = pwd_context.hash("demo123")

conn = sqlite3.connect('taxshield.db')
c = conn.cursor()
c.execute("UPDATE users SET hashed_password = ? WHERE email = 'test@test.com'", (new_hash,))
conn.commit()
print(f"Password reset to: demo123")
print(f"Rows updated: {c.rowcount}")
conn.close()
