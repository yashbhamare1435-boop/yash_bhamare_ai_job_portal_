from flask import Flask, render_template, request, jsonify, redirect, session
import sqlite3
import os
import uuid
import pdfplumber
import google.generativeai as genai

document_text = ""
all_documents = []
uploaded_files = []
document_chunks = []

app = Flask(__name__)
app.secret_key = "yash_ai_chatbot_2026"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")
else:
    model = None
@app.route("/")
def home():
    return render_template("login.html")

# HOME
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("chatbot.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password)
        )

        user = cursor.fetchone()

        conn.close()

        if user:
            session["user"] = username
            return redirect("/dashboard")

        return "Invalid Username or Password"

    return render_template("login.html")
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")
@app.route("/register", methods=["GET","POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]

        password = request.form["password"]

        conn = sqlite3.connect("chatbot.db")

        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO users(username,password) VALUES(?,?)",
            (username,password)
        )

        conn.commit()

        conn.close()

        return redirect("/login")

    return render_template("register.html")
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()

    # Total FAQs
    cursor.execute("SELECT COUNT(*) FROM faq")
    faq_count = cursor.fetchone()[0]

    # Total Chats
    cursor.execute("SELECT COUNT(*) FROM chats")
    chat_count = cursor.fetchone()[0]

    # Uploaded Files
    file_count = len(uploaded_files)

    # Unanswered Questions
    cursor.execute("SELECT COUNT(*) FROM chats WHERE bot_reply LIKE '%Sorry%'")
    unanswered_count = cursor.fetchone()[0]

    # Most Asked Question
    cursor.execute("""
        SELECT user_message, COUNT(*)
        FROM chats
        GROUP BY user_message
        ORDER BY COUNT(*) DESC
        LIMIT 1
    """)

    result = cursor.fetchone()

    if result:
        most_question = result[0]
    else:
        most_question = "No Chats Yet"

    conn.close()

    return render_template(
        "dashboard.html",
        files=uploaded_files,
        faq_count=faq_count,
        chat_count=chat_count,
        file_count=file_count,
        unanswered_count=unanswered_count,
        most_question=most_question
    )
@app.route("/upload", methods=["POST"])
def upload():

    import os

    file = request.files.get("document")

    if not file or file.filename == "":
        return "No file selected"

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    upload_folder = os.path.join(BASE_DIR, "..", "uploads")

    file_path = os.path.join(upload_folder, file.filename)

    file.save(file_path)
    uploaded_files.append(file.filename)
    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO documents (filename) VALUES (?)",
        (file.filename,)
    )

    conn.commit()
    conn.close()
    global document_text

    if file.filename.endswith(".txt"):

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        document_text = content
        all_documents.append(content)

        print("DOCUMENT CONTENT:")
        print(content)

    elif file.filename.endswith(".pdf"):

        document_text = ""

        with pdfplumber.open(file_path) as pdf:

            for page in pdf.pages:

                text = page.extract_text()

                if text:
                    document_text += text + "\n"
        all_documents.append(document_text)
        chunk_size = 500

        for i in range(0, len(document_text), chunk_size):
            chunk = document_text[i:i+chunk_size]
            document_chunks.append(chunk)
        print("PDF CONTENT:")
        print(document_text)

    return redirect("/dashboard")
@app.route("/admin", methods=["GET", "POST"])
def admin():

    if request.method == "POST":

        question = request.form["question"]
        answer = request.form["answer"]

        conn = sqlite3.connect("chatbot.db")
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO faq (question, answer) VALUES (?, ?)",
            (question, answer)
        )

        conn.commit()
        conn.close()

    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM faq")
    faqs = cursor.fetchall()

    conn.close()

    return render_template("admin.html", faqs=faqs)


# CHATBOT
@app.route("/chat", methods=["POST"])
def chat():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())

    current_session = session["session_id"]
    data = request.get_json()
    msg = data.get("message").lower().strip()
    msg = msg.replace("?", "")
    msg = msg.replace(".", "")
    msg = msg.replace(",", "")
    reply = None

    global document_text

   # DOCUMENT SEARCH
    if reply is None and all_documents:

        words = msg.split()

        best_match = ""
        best_score = 0

        for doc in all_documents:

            paragraphs = doc.split("\n\n")

            for para in paragraphs:

                score = 0

                for word in words:

                    if len(word) > 2 and word.lower() in para.lower():
                        score += 1

                if score > best_score:
                    best_score = score
                    best_match = para

        if best_score > 0:
            reply = best_match.strip()
    # SMART FAQ SEARCH

    if reply is None:

        if "pricing" in msg:
            msg = "pricing"

        elif "service" in msg:
            msg = "services"

        elif "contact" in msg:
            msg = "contact"

        elif "refund" in msg:
            msg = "refund"
    # Greeting
    if reply is None:

        if msg in ["hello", "hi", "hii"]:
            reply = "Hi 👋 How can I help you today?"

    # FAQ SEARCH
    if reply is None:

        conn = sqlite3.connect("chatbot.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT answer FROM faq WHERE question LIKE ? LIMIT 1",
            ("%" + msg + "%",)
        )

        faq_result = cursor.fetchone()

        conn.close()

        if faq_result:
            reply = faq_result[0]
    
    # GEMINI AI
    if reply is None:

        relevant_text = ""

        for chunk in document_chunks:

            if any(word in chunk.lower() for word in msg.split()):
                relevant_text += chunk + "\n"

        prompt = f"""
    You are an AI Customer Support Assistant.

    Answer only using the company information below.

    Company Information:
    {relevant_text}

    Customer Question:
    {msg}

    If the answer is not available in the company information, reply:
    Sorry, I couldn't find that information.
    """

        try:
            response = model.generate_content(prompt)
            reply = response.text.strip()

        except Exception as e:
            print("========================")
            print("Gemini Error:", e)
            print("========================")
            reply = f"Gemini Error: {e}"
    # OTHER REPLIES
    if reply is None:

        if "contact" in msg:
            reply = "Email us at support@gmail.com"

        elif "help" in msg:
            reply = "I can help you with pricing, contact details and basic support."

        elif "bye" in msg:
            reply = "Goodbye 👋"

        else:
            reply = "Sorry 😅 I didn't understand that. Try 'help', 'price', 'contact'."

    # SAVE CHAT
    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO chats (user_message, bot_reply) VALUES (?, ?)",
        (msg, reply)
    )

    conn.commit()
    conn.close()

    return jsonify({"reply": reply})

# EDIT FAQ
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_faq(id):

    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()

    if request.method == "POST":

        question = request.form["question"]
        answer = request.form["answer"]

        cursor.execute(
            "UPDATE faq SET question = ?, answer = ? WHERE id = ?",
            (question, answer, id)
        )

        conn.commit()
        conn.close()

        return redirect("/admin")

    cursor.execute("SELECT * FROM faq WHERE id = ?", (id,))
    faq = cursor.fetchone()

    conn.close()

    return render_template("edit.html", faq=faq)


# DELETE FAQ
@app.route("/delete/<int:id>", methods=["POST"])
def delete_faq(id):

    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM faq WHERE id = ?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/admin")


# HISTORy
@app.route("/history")
def history():

    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM chats")

    chats = cursor.fetchall()

    conn.close()

    return render_template(
        "history.html",
        chats=chats
    )
@app.route("/preview")
def preview():
    return render_template("index.html")
@app.route("/analytics")
def analytics():

    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_message, COUNT(*)
        FROM chats
        GROUP BY user_message
        ORDER BY COUNT(*) DESC
    """)

    questions = cursor.fetchall()

    conn.close()

    return render_template(
        "analytics.html",
        questions=questions
    )
@app.route("/embed")
def embed():

    embed_code = """
<iframe
src="http://127.0.0.1:5000"
width="400"
height="600"
style="border:none;border-radius:10px;">
</iframe>
"""

    return render_template(
        "embed.html",
        embed_code=embed_code
    )

@app.route("/delete_file/<filename>")
def delete_file(filename):

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    upload_folder = os.path.join(BASE_DIR, "..", "uploads")

    file_path = os.path.join(upload_folder, filename)

    if os.path.exists(file_path):
        os.remove(file_path)

    if filename in uploaded_files:
        uploaded_files.remove(filename)

    return redirect("/dashboard")
@app.route("/documents")
def documents():

    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM documents")
    docs = cursor.fetchall()

    conn.close()

    return render_template("documents.html", docs=docs)
# RUN APP
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)