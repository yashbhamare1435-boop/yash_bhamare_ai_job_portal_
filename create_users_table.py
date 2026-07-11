import sqlite3

conn = sqlite3.connect("chatbot.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    email TEXT UNIQUE,
    password TEXT
)
""")

conn.commit()
conn.close()

print("Users table created successfully")