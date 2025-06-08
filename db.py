# db.py

import sqlite3
from config import DB_PATH

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS downloads (
            user_id INTEGER PRIMARY KEY,
            count INTEGER DEFAULT 0,
            lang TEXT DEFAULT 'ru'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            username TEXT PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()

def add_channel(username: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO channels (username) VALUES (?)", (username,))
    conn.commit()
    conn.close()

def remove_channel(username: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM channels WHERE username = ?", (username,))
    conn.commit()
    conn.close()

def get_channels():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username FROM channels")
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]


def set_user_language(user_id: int, lang: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO downloads (user_id, lang, count)
        VALUES (?, ?, 0)
        ON CONFLICT(user_id) DO UPDATE SET lang = excluded.lang
    """, (user_id, lang))
    conn.commit()
    conn.close()

def get_user_language(user_id: int) -> str:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT lang FROM downloads WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 'ru'

def increment_user_downloads(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO downloads (user_id, count)
        VALUES (?, 1)
        ON CONFLICT(user_id) DO UPDATE SET count = count + 1
    """, (user_id,))
    conn.commit()
    conn.close()

def get_user_downloads(user_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT count FROM downloads WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0
