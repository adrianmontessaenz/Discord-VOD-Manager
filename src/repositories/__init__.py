"""Repository layer.

- VodRepository: VODs (video, channel, date, players, characters, tournament).
  Yggdrasil owns them (YggdrasilVodRepository); SQLite is a local cache/fallback.
- GuildSettingsRepository: per-server settings, filters and publication history.
  Stays in Ratatoskr.
"""
from .models import Vod
from .vod_repository import VodRepository, SqliteVodRepository
from .guild_settings import SqliteGuildSettingsRepository
from .sync_state import SqliteSyncStateRepository
from .yggdrasil_client import (YggdrasilClient, YggdrasilError, YggdrasilUnavailable,
                               YggdrasilVodRepository, build_vod_repository, vod_from_json)

__all__ = ["Vod", "VodRepository", "SqliteVodRepository", "SqliteGuildSettingsRepository",
           "SqliteSyncStateRepository", "YggdrasilClient", "YggdrasilError", "YggdrasilUnavailable",
           "YggdrasilVodRepository", "build_vod_repository", "vod_from_json"]
