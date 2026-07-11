import sqlite3

conn = sqlite3.connect("chatbot.db")

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS chats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_message TEXT,
    bot_reply TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS faq (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT,
    answer TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)
""")
cursor.execute(
    "INSERT INTO faq (question, answer) VALUES (?, ?)",
    ("price", "Our plans start from ₹499.")
)
cursor.execute(
    "INSERT INTO faq (question, answer) VALUES (?, ?)",
    ("contact", "Email us at support@gmail.com")
)
cursor.execute(
    "INSERT INTO faq (question, answer) VALUES (?, ?)",
    ("help", "I can help you with pricing, contact details and basic support.")
)
conn.commit()

conn.close()

print("Database Created Successfully")