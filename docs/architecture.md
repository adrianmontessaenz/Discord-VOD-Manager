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
- **YouTube Data API v3**: API key from `YOUTUBE_API_KEY`; quota-limited. Used for the channel uploads playlist and channel search.
- Libraries: `discord.py`, `google-api-python-client`, `python-dotenv` (unpinned in `requirements.txt`); `pytest` for tests.

## Ecosystem integration
Ratatoskr belongs to the Smash group; its tree is **Yggdrasil** (own API + Postgres). Ratatoskr never reads Yggdrasil's SQL, only its API with a per-app token, over Tailscale.

| Data | Goes to | Reason |
|---|---|---|
| VODs (video, YouTube channel, date, players, characters, tournament) | Yggdrasil | Shared with other Smash apps (Tyr, Mimir, Odín). |
| Server and channel configuration | Stays in Ratatoskr | Policy of each Discord server. |
| Filters (players, characters, YouTube sources, `enforce_*`) | Stays in Ratatoskr | Per-server preferences, not shared data. |
| Publication history (what was posted where) | Stays in Ratatoskr | Specific to Discord messages. |
| Discord token and YouTube key | Stays in Ratatoskr (secrets later in Portunus) | Secrets never go to git or to a tree. |

**Access interface needed:** `VodRepository` (`save`, `get`, `list`). Today `SqliteVodRepository` implements it locally; in Phase 1 an Yggdrasil API client will implement the same interface, with the SQLite one as fallback and shared contract tests. `GuildSettingsRepository` stays SQLite.

## Decisions
- Split the code into `VodRepository` and the settings repository, with the same SQLite file and no data migration (2026-11-10).
- Kept the table `channel_videos` as publication history and added a separate `vods` table, so existing databases keep working (2026-11-10).
- Did not fix the known bugs listed in the roadmap; Phase 0 only reorganises code (2026-11-10).
- `.env` is git-ignored and was checked: it has never been in the git history (2026-11-10).
