import sqlite3

DB_PATH = "dejaview.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_name TEXT UNIQUE,
            file_path TEXT,
            fingerprint TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS similarity_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_video TEXT,
            matched_video TEXT,
            distance INTEGER,
            label TEXT,
            UNIQUE (query_video, matched_video)
        )
    """)

    conn.commit()
    cur.close()
    conn.close()