import sqlite3
import uuid
from datetime import datetime
from contextlib import contextmanager

DB_PATH = "medisense.db"


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT 'New Chat',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conversation
                ON messages(conversation_id, created_at);
        """)


def _now():
    return datetime.utcnow().isoformat()


def create_conversation(title="New Chat"):
    conv_id = str(uuid.uuid4())
    now = _now()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (conv_id, title, now, now),
        )
    return {"id": conv_id, "title": title, "created_at": now, "updated_at": now}


def list_conversations():
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT c.id, c.title, c.created_at, c.updated_at,
                   (SELECT content FROM messages m
                    WHERE m.conversation_id = c.id AND m.role = 'user'
                    ORDER BY m.created_at ASC LIMIT 1) AS preview
            FROM conversations c
            ORDER BY c.updated_at DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_conversation(conv_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ?",
            (conv_id,),
        ).fetchone()
    return dict(row) if row else None


def delete_conversation(conv_id):
    with get_db() as conn:
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
        conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))


def rename_conversation(conv_id, title):
    with get_db() as conn:
        conn.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (title[:80], _now(), conv_id),
        )


def add_message(conv_id, role, content):
    now = _now()
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (conv_id, role, content, now),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conv_id),
        )
        msg_id = cur.lastrowid
    return {"id": msg_id, "role": role, "content": content, "created_at": now}


def get_messages(conv_id, limit=None):
    query = """
        SELECT id, role, content, created_at
        FROM messages
        WHERE conversation_id = ?
        ORDER BY created_at ASC
    """
    params = [conv_id]
    if limit:
        query = f"""
            SELECT id, role, content, created_at FROM (
                SELECT id, role, content, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ) sub ORDER BY created_at ASC
        """
        params = [conv_id, limit]

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_recent_history(conv_id, max_pairs=4):
    messages = get_messages(conv_id)
    return messages[-(max_pairs * 2):]
