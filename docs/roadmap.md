# Roadmap — Ratatoskr

## Vision
Ratatoskr is a Discord bot that watches YouTube channels for Super Smash Bros. tournament uploads and posts the VODs each server cares about, filtered by players and characters. Like the squirrel that runs up and down Yggdrasil carrying messages, it carries VODs to the people who want them. Within the Smash group Yggdrasil will query YouTube itself: Ratatoskr registers the watched channels there and reads the new VODs, keeping only each server's settings, filters and what it already posted.

## MVP
Status according to the code (not the README):

- [x] Monitors a list of YouTube channels (22 defaults in `data/config.json`) through the uploads playlist.
- [x] Per-server and per-channel configuration stored in SQLite, loaded on start.
- [x] Player filters (player 1 / player 2) matched against video titles.
- [x] Commands to add, remove and list players, characters and YouTube channels, with paginated embeds.
- [x] `!get_old_videos` fetches the history (back to 2019) sorted oldest first; `!update_frequently` polls every 15 minutes.
- [x] Repository layer separating VODs from server settings and publication history.
- [x] Character filter works (`src/filters.py`, tested).
- [x] `enforce_*` commands work and `enforce_character_2` is registered.
- [x] Duplicate posts are prevented (claim-before-send on `(guild, channel, video_id)`, tested across restarts).
- [x] Deleting a bot message removes it from the history (`on_message_delete`, one URL at a time).
- [x] `!remove_youtube_channel`, `!add_youtube_channel` by `UC` id and `on_ready` with several servers work.
- [ ] Automated tests cover the Discord commands (repositories, Yggdrasil client, filters, sync and channel sources are tested; `bot.py` is not).
- [ ] Docker image runs the bot (it ends in `CMD ["bash"]`) and dependencies are pinned.
- [x] README describes the current app.

## Milestones

### M1 — Close the MVP (0.4.0)
- **Goal:** make every feature promised in the README work reliably.
- **Tasks:** fix the unticked MVP items above; pin dependencies; make the Docker image start the bot; add tests for filters and commands; parse players, characters and tournament out of titles into `Vod`.
- **Done when:** all MVP boxes are ticked and the tests pass.

### M2 — Register channels in Yggdrasil and read their VODs (Phase 1) — implemented, pending a live check
- **Goal:** Ratatoskr stops calling YouTube; Yggdrasil watches the channels and holds the VOD catalogue.
- **Tasks:** register the watched YouTube channels in Yggdrasil (`/v1/sources/youtube`); read new VODs with `GET /v1/vods?since=<revision>`, keeping the last revision read, and apply each server's filters (players, characters) locally; implement an Yggdrasil API implementation of `VodRepository` (per-app token, via Tailscale); remove the YouTube client and `YOUTUBE_API_KEY` from Ratatoskr once it works; keep `SqliteVodRepository` as local fallback; shared contract tests for both; keep configuration, filters and publication history in local SQLite.
- **Done when:** Ratatoskr posts the same VODs from Yggdrasil as it did from YouTube, without making any call to YouTube.
- **Status:** implemented and tested against a fake Yggdrasil. Still to do: a smoke test against a real Yggdrasil and Discord.

### M3 — Turn the bot into an application (Phase 2)
- **Goal:** let Ratatoskr be used and configured as an app, not only through Discord commands.
- **Tasks:** define the app surface (settings, VOD browser, publication status) on top of the repositories; run the bot as a supervised service in Docker; keep the Discord bot as one entry point.
- **Done when:** servers can be configured and VODs browsed without typing bot commands.

## Out of scope
- Direct access to Yggdrasil's database (always through its API).
- Hosting Ratatoskr on the Internet: it stays local or behind Tailscale.
- Rankings, player results and tournament data beyond what a VOD title tells (they belong to Tyr).
- Downloading or re-hosting videos: only links are posted.
- Secrets in git or in the tree.
