"""VOD repository: the only place that knows where VODs are stored."""
import sqlite3
from typing import List, Optional, Protocol

from .models import Vod


class VodRepository(Protocol):
    """Access interface for VODs. Today: SQLite. Phase 1: Yggdrasil API client."""

    def save(self, vod: Vod) -> None: ...
    def get(self, video_id: str) -> Optional[Vod]: ...
    def list(self, youtube_channel_id: Optional[str] = None) -> List[Vod]: ...


class SqliteVodRepository:
    """Local VOD catalogue in table `vods` (global, not per Discord server)."""

    def __init__(self, db_path="data/database.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS vods (
            video_id TEXT PRIMARY KEY,
            title TEXT,
            url TEXT,
            published_at TEXT,
            youtube_channel_id TEXT,
            players TEXT,
            characters TEXT,
            tournament TEXT
        )""")
        self.conn.commit()

    def save(self, vod: Vod) -> None:
        self.conn.execute("""
        INSERT OR REPLACE INTO vods
        (video_id, title, url, published_at, youtube_channel_id, players, characters, tournament)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", (
            vod.video_id, vod.title, vod.url, vod.published_at, vod.youtube_channel_id,
            "\n".join(vod.players), "\n".join(vod.characters), vod.tournament))
        self.conn.commit()

    def get(self, video_id: str) -> Optional[Vod]:
        row = self.conn.execute("SELECT * FROM vods WHERE video_id = ?", (video_id,)).fetchone()
        return self._to_vod(row) if row else None

    def list(self, youtube_channel_id: Optional[str] = None) -> List[Vod]:
        if youtube_channel_id is None:
            rows = self.conn.execute("SELECT * FROM vods ORDER BY published_at").fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM vods WHERE youtube_channel_id = ? ORDER BY published_at",
                (youtube_channel_id,)).fetchall()
        return [self._to_vod(r) for r in rows]

    @staticmethod
    def _to_vod(row) -> Vod:
        return Vod(
            video_id=row["video_id"], title=row["title"], url=row["url"],
            published_at=row["published_at"], youtube_channel_id=row["youtube_channel_id"],
            players=tuple(p for p in (row["players"] or "").split("\n") if p),
            characters=tuple(c for c in (row["characters"] or "").split("\n") if c),
            tournament=row["tournament"])
