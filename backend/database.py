"""database.py - all SQL (SQLite) code lives here."""
import os
import sqlite3

if os.getenv("VERCEL"):
    # Vercel function files are read-only; /tmp is writable but ephemeral.
    DB_PATH = os.path.join(os.getenv("TMPDIR", "/tmp"), "heta.db")
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), "heta.db")


def get_conn():
    """Open a connection. Rows behave like dictionaries."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # lets ON DELETE CASCADE work
    return conn


def init_db():
    """Create the tables (if missing) and a default guest user."""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT 'New Chat',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,            -- 'user' or 'assistant'
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        );
    """)
    # Login is not part of this version, so everyone chats as user #1 (guest).
    conn.execute(
        "INSERT OR IGNORE INTO users (id, username, email, password) "
        "VALUES (1, 'guest', 'guest@heta.ai', 'not-used')"
    )
    conn.commit()
    conn.close()


def create_conversation(title="New Chat", user_id=1):
    conn = get_conn()
    cur = conn.execute("INSERT INTO conversations (user_id, title) VALUES (?, ?)", (user_id, title))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def list_conversations(user_id=1):
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, title, created_at FROM conversations WHERE user_id = ? ORDER BY id DESC", (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def conversation_exists(conversation_id):
    conn = get_conn()
    row = conn.execute("SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
    conn.close()
    return row is not None


def get_messages(conversation_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, role, message, created_at FROM messages WHERE conversation_id = ? ORDER BY id",
        (conversation_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_message(conversation_id, role, message):
    conn = get_conn()
    conn.execute(
        "INSERT INTO messages (conversation_id, role, message) VALUES (?, ?, ?)",
        (conversation_id, role, message),
    )
    conn.commit()
    conn.close()


def delete_last_assistant_message(conversation_id):
    """Used by 'Regenerate': remove the newest AI answer."""
    conn = get_conn()
    conn.execute(
        "DELETE FROM messages WHERE id = (SELECT id FROM messages WHERE conversation_id = ? "
        "AND role = 'assistant' ORDER BY id DESC LIMIT 1)",
        (conversation_id,),
    )
    conn.commit()
    conn.close()


def clear_messages(conversation_id):
    conn = get_conn()
    conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
    conn.commit()
    conn.close()


def rename_conversation(conversation_id, title):
    conn = get_conn()
    conn.execute("UPDATE conversations SET title = ? WHERE id = ?", (title, conversation_id))
    conn.commit()
    conn.close()


def delete_conversation(conversation_id):
    conn = get_conn()
    conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    conn.commit()
    conn.close()
