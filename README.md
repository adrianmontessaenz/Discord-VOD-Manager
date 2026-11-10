# Ratatoskr
**Smash VODs for Discord**

[![Status](https://img.shields.io/badge/status-in%20development-orange)](#)
[![Language](https://img.shields.io/badge/language-Python-blue?logo=python)](https://python.org/)
[![Python](https://img.shields.io/badge/python-3.11+-blue?logo=python)](https://python.org/)
[![Discord.py](https://img.shields.io/badge/discord.py-2.6.4-5865F2?logo=discord)](https://discordpy.readthedocs.io/)
[![YouTube API](https://img.shields.io/badge/API-YouTube-red?logo=youtube)](https://developers.google.com/youtube/v3)

Discord VOD Manager is a Discord bot that automatically monitors YouTube channels for Super Smash Bros. tournament uploads and posts relevant VODs to Discord servers. Server administrators can configure channels, players, and game-specific filters to receive only the matches they care about, while the bot records previously posted videos (duplicate prevention is still being fixed) and provides continuous updates as new tournament content becomes available.

## **Why "Ratatoskr"**
Ratatoskr is the squirrel of Norse myth that runs up and down Yggdrasil carrying messages between the eagle and the serpent: this bot carries Smash VODs to the Discord servers that want them. The project (repository `Discord-VOD-Manager`) belongs to the Smash group of apps, whose shared backend will be the tree Yggdrasil. See [minerva.yaml](minerva.yaml), the [roadmap](docs/roadmap.md), the [architecture](docs/architecture.md) and the [changelog](CHANGELOG.md).

## **Features**

This application currently includes/will include the following features (see the [roadmap](docs/roadmap.md) for which ones already work):

* Monitor multiple YouTube channels for new tournament uploads.
* Filter videos by player tags to receive only relevant matches.
* Filter videos by character selections for more precise results (known bug, see the roadmap).
* Support multiple Discord servers and channels with independent configurations.
* Record previously posted videos to prevent duplicate uploads (known bug, see the roadmap).
* Retrieve historical VODs from monitored channels and sort them chronologically.
* Configure channel-specific settings such as player filters, character filters, and posting behavior.
* Persist configuration and posting history using SQLite.
* Run automated background checks for newly uploaded videos.
* Provide Discord commands for managing tracked players, characters, and YouTube channels.
* Support Unicode player and character names, including Japanese characters.
* Generate embedded Discord messages for improved readability and user interaction.

## **Challenges of the project**
* Handling asynchronous execution in Discord.py without blocking the bot while fetching YouTube data.
* Managing YouTube Data API limitations, including pagination, missing metadata fields, and quota constraints.
* Designing a reliable system to prevent duplicate video postings across multiple servers and channels.
* Dealing with inconsistent or missing metadata from YouTube (e.g., category fields, topic details, and game tags).
* Normalizing and comparing datetime values with timezones when sorting and filtering video uploads.
* Structuring persistent storage with SQLite while keeping runtime performance efficient for multi-guild usage.
* Balancing in-memory caching versus database queries to reduce latency without losing data consistency.
* Supporting flexible user-defined filters (players, characters, and channels) with scalable data structures.
* Ensuring stability of background tasks that continuously fetch and process video data.
* Handling real-world naming conflicts, such as identical player tags across different games or communities.

