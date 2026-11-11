"""Publishes new VODs read from Yggdrasil to Discord channels. No Discord imports: `send` is injected."""
import asyncio
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Awaitable, Callable, Dict, FrozenSet, List, Optional, Sequence, Tuple

from filters import ChannelFilter, vod_matches
from repositories import (SqliteGuildSettingsRepository, SqliteSyncStateRepository,
                          SqliteVodRepository, Vod, VodRepository)

CURSOR_KEY = "vods_revision"

Send = Callable[[int, int, str], Awaitable[bool]]  # (guild_id, channel_id, text) -> False if unreachable


@dataclass(frozen=True)
class ChannelTarget:
    guild_id: int
    channel_id: int
    youtube_channel_ids: FrozenSet[str]
    filter: ChannelFilter


@dataclass
class SyncResult:
    published: int = 0
    revision: Optional[int] = None
    initialised: bool = False


def format_vod(vod: Vod) -> str:
    try:
        when = datetime.fromisoformat(vod.published_at.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        when = vod.published_at
    return f"{vod.title} ({when}): {vod.url}"


def urls_in_message(content: str) -> List[str]:
    return [u.rstrip(".,;:!?)") for u in re.findall(r"https?://[^\s<>]+", content)]


async def publish_new_vods(*, source: VodRepository, state: SqliteSyncStateRepository,
                           settings: SqliteGuildSettingsRepository,
                           cache: Optional[SqliteVodRepository],
                           targets: Sequence[ChannelTarget], send: Send,
                           char_aliases: Optional[Dict[str, Tuple[str, ...]]] = None,
                           delay: float = 3.0) -> SyncResult:
    """One sync tick. Each (guild, channel, video) is claimed in SQLite before sending, so
    restarts, retries and revision bumps never post the same VOD twice."""
    cursor = state.get(CURSOR_KEY)
    if cursor is None:
        revision = source.latest_revision()
        state.set(CURSOR_KEY, str(revision))
        return SyncResult(revision=revision, initialised=True)

    vods = source.list(since_revision=int(cursor))  # YggdrasilError propagates before any change
    result = SyncResult()
    if not vods:
        return result
    if cache is not None:
        for vod in vods:
            cache.save(vod)

    for vod in sorted(vods, key=lambda v: v.published_at):
        for t in targets:
            if vod.youtube_channel_id not in t.youtube_channel_ids:
                continue
            if not vod_matches(vod, t.filter, char_aliases):
                continue
            if not settings.add_published(t.guild_id, t.channel_id, vod.video_id,
                                          vod.title, vod.url, vod.published_at):
                continue
            try:
                ok = await send(t.guild_id, t.channel_id, format_vod(vod))
            except BaseException:
                settings.remove_published(t.guild_id, t.channel_id, vod.video_id)
                raise
            if not ok:
                settings.remove_published(t.guild_id, t.channel_id, vod.video_id)
                continue
            result.published += 1
            await asyncio.sleep(delay)

    result.revision = max(v.revision for v in vods)
    state.set(CURSOR_KEY, str(result.revision))
    return result
