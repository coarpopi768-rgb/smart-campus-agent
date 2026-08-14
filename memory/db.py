"""Memory database —— SQLite 表结构和连接管理"""
import sqlite3, json, threading
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).parent.parent / 'data' / 'agent_memory.db'
_local = threading.local()


def _get_conn():
    if not hasattr(_local, 'conn') or _local.conn is None:
        _local.conn = sqlite3.connect(str(DB_PATH))
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute('PRAGMA journal_mode=WAL')
        _local.conn.execute('PRAGMA foreign_keys=ON')
    return _local.conn


@contextmanager
def get_cursor():
    conn = _get_conn()
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def init_memory_tables():
    """初始化记忆相关表（安全：CREATE IF NOT EXISTS，可重复执行）"""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with get_cursor() as cur:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS user_profile (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL DEFAULT 'guest',
                student_id TEXT,
                display_name TEXT NOT NULL DEFAULT '用户',
                department TEXT,
                grade TEXT,
                preferences TEXT DEFAULT '{}',
                interaction_count INTEGER DEFAULT 0,
                last_seen_at TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                updated_at TEXT DEFAULT (datetime('now','localtime'))
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS user_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                fact TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                source_session TEXT,
                importance INTEGER DEFAULT 1 CHECK(importance BETWEEN 1 AND 5),
                access_count INTEGER DEFAULT 0,
                last_accessed_at TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (user_id) REFERENCES user_profile(user_id)
            )
        ''')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_memory_user ON user_memory(user_id)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_memory_category ON user_memory(user_id, category)')
