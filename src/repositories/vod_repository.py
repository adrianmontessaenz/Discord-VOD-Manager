"""VOD repository: the only place that knows where VODs are stored."""
import sqlite3
from typing import List, Optional, Protocol

from .models import Vod


class VodRepository(Protocol):
    """Read interface for VODs. Yggdrasil owns the data; SQLite is a local cache/fallback.

    `save` is deliberately not part of the protocol: it lives on SqliteVodRepository only.
    """

    def get(self, video_id: str) -> Optional[Vod]: ...
    def list(self, youtube_channel_id: Optional[str] = None,
             since_revision: Optional[int] = None) -> List[Vod]: ...
    def latest_revision(self) -> int: ...


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
            tournament TEXT,
            revision INTEGER NOT NULL DEFAULT 0
        )""")
        columns = [r["name"] for r in self.conn.execute("PRAGMA table_info(vods)")]
        if "revision" not in columns:
            self.conn.execute("ALTER TABLE vods ADD COLUMN revision INTEGER NOT NULL DEFAULT 0")
        self.conn.commit()

    def save(self, vod: Vod) -> None:
        self.conn.execute("""
        INSERT OR REPLACE INTO vods
        (video_id, title, url, published_at, youtube_channel_id, players, characters, tournament, revision)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
            vod.video_id, vod.title, vod.url, vod.published_at, vod.youtube_channel_id,
            "\n".join(vod.players), "\n".join(vod.characters), vod.tournament, vod.revision))
        self.conn.commit()

    def get(self, video_id: str) -> Optional[Vod]:
        row = self.conn.execute("SELECT * FROM vods WHERE video_id = ?", (video_id,)).fetchone()
        return self._to_vod(row) if row else None

    def list(self, youtube_channel_id: Optional[str] = None,
             since_revision: Optional[int] = None) -> List[Vod]:
        where, params = [], []
        if youtube_channel_id is not None:
            where.append("youtube_channel_id = ?")
            params.append(youtube_channel_id)
        if since_revision is not None:
            where.append("revision > ?")
            params.append(since_revision)
        sql = "SELECT * FROM vods"
        if where:
            sql += " WHERE " + " AND ".join(where)
        rows = self.conn.execute(sql + " ORDER BY published_at", params).fetchall()
        return [self._to_vod(r) for r in rows]

    def latest_revision(self) -> int:
        return self.conn.execute("SELECT COALESCE(MAX(revision), 0) FROM vods").fetchone()[0]

    @staticmethod
    def _to_vod(row) -> Vod:
        return Vod(
            video_id=row["video_id"], title=row["title"], url=row["url"],
            published_at=row["published_at"], youtube_channel_id=row["youtube_channel_id"],
            players=tuple(p for p in (row["players"] or "").split("\n") if p),
            characters=tuple(c for c in (row["characters"] or "").split("\n") if c),
            tournament=row["tournament"], revision=row["revision"])
