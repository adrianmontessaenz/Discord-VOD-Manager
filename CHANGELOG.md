# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/). While there is no `1.0.0`, minor versions may include breaking changes.

## [Unreleased]

### Added
- Ecosystem documents: `minerva.yaml`, `docs/roadmap.md`, `docs/architecture.md` and `CHANGELOG.md` (2026-11-10).
- Repository layer in `src/repositories/`: `VodRepository` for VODs and a settings repository for server configuration and publication history, with tests (2026-11-10).
- `.env.example` with the required variable names (2026-11-10).

### Changed
- `src/database.py` moved to `src/repositories/guild_settings.py` and renamed; video-history methods are now `add_published`, `get_published` and `remove_published_by_url` (2026-11-10).
- Every video that passes the filters is now also saved in a local `vods` table (2026-11-10).
- README now has the codename header and the "Why" section, and no longer claims unfinished behaviour (2026-06-11, 2026-11-10).

## [0.3.0] - 2026-02-14

Separate filters per player and fixes after real use.

### Added
- Separate `_1` / `_2` commands for players and characters, each with its own `enforce` option stored per channel (2026-02-14).

### Changed
- Config and database code reworked to store the new options (2026-02-14).

### Fixed
- Invalid dates in `!get_old_videos` now return an error message instead of being ignored, plus other fixes and input checks found while testing (2026-02-13).

## [0.2.0] - 2026-02-11

### Added
- SQLite persistence of server configuration, filters, YouTube channels and posted videos (2026-02-11).
- Automatic reload of each server's configuration when the bot starts (2026-02-11).

## [0.1.0] - 2026-02-10

First usable version: a Discord bot that fetches Smash tournament VODs from YouTube channels and filters them by players and characters.

### Added
- Bot skeleton with the YouTube uploads search and a Dockerfile for development (2026-02-10).
- Commands to add, remove and list players, characters and YouTube channels, `!get_old_videos`, automatic updates every 15 minutes and `!help` (2026-02-10).
- Default list of YouTube channels and character names in several languages in `data/config.json` (2026-02-10).
