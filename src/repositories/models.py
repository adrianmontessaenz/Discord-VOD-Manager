"""Domain models shared by the repositories."""
from dataclasses import dataclass, field
from typing import Optional, Tuple


@dataclass(frozen=True)
class Vod:
    """A Smash VOD. This is the data that will move to Yggdrasil in Phase 1.

    players, characters and tournament are not extracted from titles yet: they
    stay empty until the parsing exists (see docs/roadmap.md).
    """
    video_id: str
    title: str
    url: str
    published_at: str  # ISO 8601, as returned by YouTube
    youtube_channel_id: Optional[str] = None
    players: Tuple[str, ...] = field(default_factory=tuple)
    characters: Tuple[str, ...] = field(default_factory=tuple)
    tournament: Optional[str] = None
    revision: int = 0
