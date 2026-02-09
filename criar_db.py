# test_db.py
import os
import psycopg2

url = os.environ.get("DATABASE_URL")
print("DATABASE_URL:", url)

conn = psycopg2.connect(url, connect_timeout=10)
print("Conectou!")
cur = conn.cursor()
cur.execute("select 1;")
print(cur.fetchone())
conn.close()
