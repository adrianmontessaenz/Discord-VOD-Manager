# Architecture — Ratatoskr

## Current architecture
Ratatoskr is a Discord bot (`discord.py`, prefix `!`) that runs as a single Python process. It stores its data in a local SQLite file and uses the network only to call Yggdrasil (VODs and watched channels) and Discord. It never calls YouTube.

```
  Discord commands / events / background tasks      src/bot.py
                      |
          in-memory config + title filter           src/config.py
                      |
        repositories (interfaces + SQLite)          src/repositories/
          |                          |
  VodRepository          GuildSettingsRepository
  (VODs)                 (settings, filters, published)
          |                          |
        data/database.db (SQLite)    data/config.json (defaults)
                      |
     Yggdrasil API (/v1, Bearer token)
```

- **Bot** (`src/bot.py`): commands, Discord events, paginated embeds and one `tasks.loop` every 15 minutes that serves every channel with `auto_update` enabled, plus one asyncio task per channel for `!get_old_videos`.
- **Config** (`src/config.py`): `MyConfig` keeps each channel's filters and YouTube channels in memory, registers channels in Yggdrasil and builds the `ChannelTarget`s for the sync.
- **Filters** (`src/filters.py`): `ChannelFilter` and `vod_matches`; accent- and case-insensitive token matching with character aliases.
- **Sync** (`src/vod_sync.py`): `publish_new_vods` reads VODs since the stored revision, filters them per channel, claims each `(guild, channel, video)` in SQLite and then sends. No Discord imports; `send` is injected.
- **Yggdrasil client** (`src/repositories/yggdrasil_client.py`): HTTP client and `YggdrasilVodRepository` (`VodRepository` over the API); `build_vod_repository()` falls back to the local SQLite repository when `YGGDRASIL_URL` / `YGGDRASIL_TOKEN` are not set.
- **VOD repository** (`src/repositories/vod_repository.py`): `VodRepository` protocol and its SQLite implementation. It is the only place that knows where VODs live.
- **Settings repository** (`src/repositories/guild_settings.py`): server configuration, filters and the history of posted videos.
- **Models** (`src/repositories/models.py`): the `Vod` dataclass.
- **Tests** (`tests/`): repositories (shared contract for both `VodRepository` implementations), Yggdrasil client, filters, sync and channel sources, all over a fake Yggdrasil (`tests/fakes.py`); they also check that only the repository package imports `sqlite3` and that nothing references YouTube. The Discord commands have no tests.

## Data model
SQLite file `data/database.db`, no schema versioning; tables are created with `CREATE TABLE IF NOT EXISTS` on start.

| Entity | Table(s) | Notes |
|---|---|---|
| VOD | `vods` | Local cache of what was read from Yggdrasil; `revision` column. Global (not per server). Key `video_id`. `players` and `characters` are newline-joined text; `tournament` and the lists are empty until titles are parsed. |
| Discord channel settings | `channels` | Key `(guild_id, channel_id)`; flags `enforce_character_1/2`, `enforce_player_1/2` and `auto_update`. |
| Character filters | `channel_characters_1`, `channel_characters_2` | One row per character name (English key). |
| Player filters | `channel_players_1`, `channel_players_2` | One row per tag. |
| YouTube sources | `channel_youtube` | Key `(guild_id, channel_id, youtube_channel_id)`; stores the channel name. |
| Sync cursor | `sync_state` | Key `vods_revision`: last Yggdrasil revision processed. |
| Publication history | `channel_videos` | Key `(guild_id, channel_id, video_id)`: what was already posted where. Name kept to avoid a migration. |

Outside the database: `.env` (`DISCORD_BOT_TOKEN`, `YGGDRASIL_URL`, `YGGDRASIL_TOKEN`; git-ignored) and `data/config.json` (default YouTube channels and character names with translations).

## External dependencies
- **Discord API**: bot token from `DISCORD_BOT_TOKEN`; needs the message content intent.
- **Yggdrasil API** (`/v1`): per-app Bearer token; `sources/youtube` (list, add, remove, history) and `vods?since=<revision>`. If it is down, the sync keeps its cursor and retries on the next tick; commands that need it say so.
- Libraries: `discord.py`, `requests`, `python-dotenv` (unpinned in `requirements.txt`); `pytest` for tests.

## Ecosystem integration
Ratatoskr belongs to the Smash group; its tree is **Yggdrasil** (own API + Postgres). Ratatoskr never reads Yggdrasil's SQL, only its API with a per-app token, over Tailscale.

| Data | Goes to | Reason |
|---|---|---|
| VODs (video, YouTube channel, date, players, characters, tournament) | Yggdrasil | Shared with other Smash apps (Tyr, Mimir, Odín). |
| Server and channel configuration | Stays in Ratatoskr | Policy of each Discord server. |
| Watched YouTube channels (global list) | Yggdrasil (`/v1/sources/youtube`) | Yggdrasil queries YouTube; Ratatoskr only registers the channels. Each server's choice of channels stays local. |
| Filters (players, characters, `enforce_*`) | Stays in Ratatoskr | Per-server preferences, applied locally over the VODs read. |
| Publication history (what was posted where) | Stays in Ratatoskr | Specific to Discord messages. |
| Discord token | Stays in Ratatoskr (secrets later in Portunus) | Secrets never go to git or to a tree. The YouTube key moves to Yggdrasil in Phase 1. |

**YouTube is queried by Yggdrasil, not by Ratatoskr.** From Phase 1 Ratatoskr no longer calls YouTube (nor needs `YOUTUBE_API_KEY`). It registers the watched channels in Yggdrasil (`/v1/sources/youtube`) and reads new VODs with `GET /v1/vods?since=<revision>`, applying each server's player and character filters locally. Configuration, filters and publication history stay in its SQLite.

**Access interface:** `VodRepository` (`get`, `list(since_revision)`, `latest_revision`). `YggdrasilVodRepository` and `SqliteVodRepository` implement it and pass the same contract tests; `save` exists only on the SQLite one (the cache). `GuildSettingsRepository` stays SQLite.

## Decisions
- The first sync only records the latest revision and posts nothing; from then on every VOD is claimed in `channel_videos` before it is sent and the claim is released if sending fails, so restarts and revision bumps never repost (2026-11-11).
- `auto_update` is stored per channel in SQLite and one loop serves all channels; the revision cursor is global (2026-11-11).
- A channel is added locally only after Yggdrasil accepted it (2026-11-11).
- Yggdrasil queries YouTube itself; Ratatoskr registers channels in `/v1/sources/youtube`, reads VODs with `GET /v1/vods?since=<revision>` and filters per server locally. Configuration, filters and publication history stay in SQLite (2026-11-10).
- Split the code into `VodRepository` and the settings repository, with the same SQLite file and no data migration (2026-11-10).
- Kept the table `channel_videos` as publication history and added a separate `vods` table, so existing databases keep working (2026-11-10).
- Did not fix the known bugs listed in the roadmap; Phase 0 only reorganises code (2026-11-10).
- `.env` is git-ignored and was checked: it has never been in the git history (2026-11-10).
