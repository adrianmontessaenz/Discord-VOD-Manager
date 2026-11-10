# Architecture — Ratatoskr

## Current architecture
Ratatoskr is a Discord bot (`discord.py`, prefix `!`) that runs as a single Python process. It stores its data in a local SQLite file and uses the network only to call the YouTube Data API and Discord.

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
            YouTube Data API v3
```

- **Bot** (`src/bot.py`): commands, Discord events, paginated embeds and one asyncio task per server and channel (history fetch, 15-minute updates).
- **Config and filter** (`src/config.py`): `MyConfig` keeps each channel's filters in memory, calls YouTube and matches player and character names against video titles.
- **VOD repository** (`src/repositories/vod_repository.py`): `VodRepository` protocol and its SQLite implementation. It is the only place that knows where VODs live.
- **Settings repository** (`src/repositories/guild_settings.py`): server configuration, filters and the history of posted videos.
- **Models** (`src/repositories/models.py`): the `Vod` dataclass.
- **Tests** (`tests/`): cover the repositories and check that only the repository package imports `sqlite3`. The commands and filters have no tests yet.

## Data model
SQLite file `data/database.db`, no schema versioning; tables are created with `CREATE TABLE IF NOT EXISTS` on start.

| Entity | Table(s) | Notes |
|---|---|---|
| VOD | `vods` | Global (not per server). Key `video_id`. `players` and `characters` are newline-joined text; `tournament` and the lists are empty until titles are parsed. |
| Discord channel settings | `channels` | Key `(guild_id, channel_id)`; flags `enforce_character_1/2`, `enforce_player_1/2`. |
| Character filters | `channel_characters_1`, `channel_characters_2` | One row per character name (English key). |
| Player filters | `channel_players_1`, `channel_players_2` | One row per tag. |
| YouTube sources | `channel_youtube` | Key `(guild_id, channel_id, youtube_channel_id)`; stores the channel name. |
| Publication history | `channel_videos` | Key `(guild_id, channel_id, video_id)`: what was already posted where. Name kept to avoid a migration. |

Outside the database: `.env` (`DISCORD_BOT_TOKEN`, `YOUTUBE_API_KEY`, git-ignored; names in `.env.example`) and `data/config.json` (default YouTube channels and character names with translations).

## External dependencies
- **Discord API**: bot token from `DISCORD_BOT_TOKEN`; needs the message content intent.
- **YouTube Data API v3**: API key from `YOUTUBE_API_KEY`; quota-limited. Used for the channel uploads playlist and channel search. Today only; in Phase 1 Yggdrasil takes over and Ratatoskr stops calling YouTube.
- Libraries: `discord.py`, `google-api-python-client`, `python-dotenv` (unpinned in `requirements.txt`); `pytest` for tests.

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

**Access interface needed:** `VodRepository` (`save`, `get`, `list`). Today `SqliteVodRepository` implements it locally; in Phase 1 an Yggdrasil API client will implement the same interface (reading by revision, registering channels), with the SQLite one as fallback and shared contract tests. `GuildSettingsRepository` stays SQLite.

## Decisions
- Yggdrasil queries YouTube itself; Ratatoskr registers channels in `/v1/sources/youtube`, reads VODs with `GET /v1/vods?since=<revision>` and filters per server locally. Configuration, filters and publication history stay in SQLite (2026-11-10).
- Split the code into `VodRepository` and the settings repository, with the same SQLite file and no data migration (2026-11-10).
- Kept the table `channel_videos` as publication history and added a separate `vods` table, so existing databases keep working (2026-11-10).
- Did not fix the known bugs listed in the roadmap; Phase 0 only reorganises code (2026-11-10).
- `.env` is git-ignored and was checked: it has never been in the git history (2026-11-10).
