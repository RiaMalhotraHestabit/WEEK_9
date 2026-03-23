import sqlite3
import os
from datetime import datetime


class LongTermMemory:
    """
    SQLite-based persistent memory.
    Stores full conversation history.
    """

    def __init__(self, db_path: str = "memory/long_term.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def add(self, role: str, content: str):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO messages (timestamp, role, content) VALUES (?, ?, ?)",
            (datetime.now().isoformat(), role, content)
        )
        conn.commit()
        conn.close()

    def get_recent(self, limit: int = 5):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT role, content FROM messages ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()

        return [
            {"role": r[0], "content": r[1]}
            for r in reversed(rows)
        ]