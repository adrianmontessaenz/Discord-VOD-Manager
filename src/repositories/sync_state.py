"""Small key/value store for sync cursors (stays in Ratatoskr)."""
import sqlite3
from typing import Optional


class SqliteSyncStateRepository:
    def __init__(self, db_path="data/database.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("CREATE TABLE IF NOT EXISTS sync_state (key TEXT PRIMARY KEY, value TEXT)")
        self.conn.commit()

    def get(self, key: str) -> Optional[str]:
        row = self.conn.execute("SELECT value FROM sync_state WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def set(self, key: str, value: str) -> None:
        self.conn.execute("INSERT OR REPLACE INTO sync_state (key, value) VALUES (?, ?)", (key, value))
        self.conn.commit()
