import os
import json
import sqlite3
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY_D3"))
DB_PATH = "memory/long_term.db"

def setup_db(db_path: str = DB_PATH): 
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS facts (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            key       TEXT UNIQUE NOT NULL,
            value     TEXT NOT NULL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS conversations (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            role      TEXT NOT NULL,
            content   TEXT NOT NULL,
            session   TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS summaries (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            session   TEXT NOT NULL,
            summary   TEXT NOT NULL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()

def store_fact(key: str, value: str, db_path: str = DB_PATH): # this function will store facts.
    conn = sqlite3.connect(db_path)
    conn.execute("""INSERT INTO facts (key, value, timestamp) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value, timestamp = excluded.timestamp
    """, (key.lower(), value, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    print(f"[LongTermMemory] Fact stored: {key} = {value}")

def get_all_facts(db_path: str = DB_PATH) -> list:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute("SELECT * FROM facts ORDER BY timestamp DESC").fetchall()]
    conn.close()
    return rows

# CONVERSATIONS
def store_message(role: str, content: str, session: str, db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO conversations (role, content, session, timestamp) VALUES (?,?,?,?)",(role, content, session, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_history(session: str, limit: int = 6, db_path: str = DB_PATH) -> list:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""SELECT role, content FROM conversations WHERE session = ? ORDER BY timestamp DESC LIMIT ?""", (session, limit)).fetchall()
    conn.close()
    return list(reversed([dict(r) for r in rows]))

def store_summary(session: str, summary: str, db_path: str = DB_PATH):   # SUMMARIES
    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO summaries (session, summary, timestamp) VALUES (?,?,?)",(session, summary, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    print(f"[LongTermMemory] Summary stored for session: {session}")

# LLM HELPERS
def extract_facts(text: str) -> list:
    """Extract key facts from text using LLM."""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": """Extract facts from user message. Return ONLY JSON:
{"facts": [{"key": "name", "value": "Ria"}]}
Only extract: name, role, company, location, project, week. If none found: {"facts": []}"""},
                {"role": "user", "content": text},],temperature=0.0, max_tokens=200,)
        raw = response.choices[0].message.content.strip().replace("```json","").replace("```","")
        return json.loads(raw).get("facts", [])
    except:
        return []

def summarize(messages: list) -> str:
    """Summarize a conversation using LLM."""
    if not messages:
        return ""
    text = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Summarize this conversation in 2-3 sentences. Focus on key facts and topics."},
                {"role": "user", "content": text},
            ],
            temperature=0.3, max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except:
        return ""

# MAIN CHAT FUNCTION
def chat(user_input: str, session: str, db_path: str = DB_PATH) -> str:
    # Extract and store facts from input
    for fact in extract_facts(user_input):
        store_fact(fact["key"], fact["value"], db_path)

    # Build context from facts + history
    facts    = get_all_facts(db_path)
    history  = get_history(session, db_path=db_path)
    facts_str   = "\n".join(f"  - {f['key']}: {f['value']}" for f in facts)
    history_str = "\n".join(f"  {m['role'].upper()}: {m['content']}" for m in history)

    context = ""
    if facts_str:
        context += f"Known facts:\n{facts_str}\n"
    if history_str:
        context += f"\nRecent history:\n{history_str}\n"

    # Call LLM
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a helpful assistant with long-term memory. Use the known facts and history to give personalized answers."},
            {"role": "user",   "content": f"{user_input}\n\n{context}"},
        ],
        temperature=0.3, max_tokens=512,
    )
    reply = response.choices[0].message.content.strip()

    # Store messages
    store_message("user", user_input, session, db_path)
    store_message("assistant", reply, session, db_path)

    return reply

if __name__ == "__main__":
    setup_db()
    session = datetime.now().strftime("%Y%m%d_%H%M%S")
    print("=" * 50)
    print("  LONG TERM MEMORY — Interactive Terminal")
    print("  'memory' → show facts | 'summarize' → summarize session | 'exit' → quit")
    print("=" * 50)

    while True:
        print()
        user_input = input("You: ").strip()

        if not user_input:
            continue
        if user_input.lower() == "exit":
            print("[LongTermMemory] Goodbye!")
            break
        if user_input.lower() == "memory":
            facts = get_all_facts()
            print(f"\n  Facts stored: {len(facts)}")
            for f in facts:
                print(f"    • {f['key']}: {f['value']}")
            continue
        if user_input.lower() == "summarize":
            history = get_history(session, limit=20)
            s = summarize(history)
            if s:
                store_summary(session, s)
                print(f"\n  Summary: {s}")
            continue
        reply = chat(user_input, session)
        print(f"\nAssistant: {reply}")