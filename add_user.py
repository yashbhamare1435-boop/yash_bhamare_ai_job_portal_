import sqlite3

conn = sqlite3.connect("chatbot.db")
cursor = conn.cursor()

cursor.execute(
    "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
    ("admin", "admin@gmail.com", "1234")
)

conn.commit()
conn.close()

print("User Added Successfully")