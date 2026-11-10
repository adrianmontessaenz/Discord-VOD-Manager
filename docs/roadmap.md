# Roadmap — Ratatoskr

## Vision
Ratatoskr is a Discord bot that watches YouTube channels for Super Smash Bros. tournament uploads and posts the VODs each server cares about, filtered by players and characters. Like the squirrel that runs up and down Yggdrasil carrying messages, it carries VODs to the people who want them. Within the Smash group it will store the VODs it finds in Yggdrasil, keeping only each server's settings and what it already posted.

## MVP
Status according to the code (not the README):

- [x] Monitors a list of YouTube channels (22 defaults in `data/config.json`) through the uploads playlist.
- [x] Per-server and per-channel configuration stored in SQLite, loaded on start.
- [x] Player filters (player 1 / player 2) matched against video titles.
- [x] Commands to add, remove and list players, characters and YouTube channels, with paginated embeds.
- [x] `!get_old_videos` fetches the history (back to 2019) sorted oldest first; `!update_frequently` polls every 15 minutes.
- [x] Repository layer separating VODs from server settings and publication history.
- [ ] Character filter works: `_MyChannels.enforce_characters` does not exist, so any video that fails the character match raises `AttributeError`.
- [ ] `enforce_*` commands work: they call `set_enforce_*` methods that do not exist in `MyConfig`; `enforce_character_2` is not registered as a command.
- [ ] Duplicate posts are prevented: `get_published` returns rows that are compared with URLs, so every video counts as new.
- [ ] Deleting a bot message removes it from the history: `on_message_deleted` is not a discord.py event (`on_message_delete`) and a list is passed as SQL parameter.
- [ ] `!remove_youtube_channel`, `!add_youtube_channel` by `UC` id and `on_ready` with several servers work (known `KeyError`, dict/list mix-up and an early `return`).
- [ ] Automated tests cover the commands and filters (only the repositories have tests).
- [ ] Docker image runs the bot (it ends in `CMD ["bash"]`) and dependencies are pinned.
- [x] README describes the current app.

## Milestones

### M1 — Close the MVP (0.4.0)
- **Goal:** make every feature promised in the README work reliably.
- **Tasks:** fix the unticked MVP items above; pin dependencies; make the Docker image start the bot; add tests for filters and commands; parse players, characters and tournament out of titles into `Vod`.
- **Done when:** all MVP boxes are ticked and the tests pass.

### M2 — Store and read VODs in Yggdrasil (Phase 1)
- **Goal:** keep the VOD catalogue in Yggdrasil instead of the local database.
- **Tasks:** implement an Yggdrasil API implementation of `VodRepository` (per-app token, via Tailscale); keep `SqliteVodRepository` as local fallback; shared contract tests for both; keep server settings and publication history local.
- **Done when:** saving and reading VODs through Yggdrasil returns the same results as the local repository.

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
