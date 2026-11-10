import sqlite3
import os

class SqliteGuildSettingsRepository:
    """Per-server settings (channels, filters, YouTube sources) and publication history.

    Stays in Ratatoskr. The table `channel_videos` is the publication history
    (what was already posted to each Discord channel), not the VOD catalogue.
    """

    def __init__(self, db_path="data/database.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._create_tables()
        
    def _create_tables(self):
        """Create the necessary tables if they don't exist."""
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            guild_id INTEGER,
            channel_id INTEGER,
            enforce_character_1 BOOLEAN DEFAULT 0,
            enforce_character_2 BOOLEAN DEFAULT 0,
            enforce_player_1 BOOLEAN DEFAULT 1,
            enforce_player_2 BOOLEAN DEFAULT 1,
            PRIMARY KEY (guild_id, channel_id)
        )""")
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel_characters_1 (
            guild_id INTEGER,
            channel_id INTEGER,
            characters TEXT,
            PRIMARY KEY (guild_id, channel_id, characters)
        )""")
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel_characters_2 (
            guild_id INTEGER,
            channel_id INTEGER,
            characters TEXT,
            PRIMARY KEY (guild_id, channel_id, characters)
        )""")
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel_players_1 (
            guild_id INTEGER,
            channel_id INTEGER,
            player TEXT,
            PRIMARY KEY (guild_id, channel_id, player)
        )""")
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel_players_2 (
            guild_id INTEGER,
            channel_id INTEGER,
            player TEXT,
            PRIMARY KEY (guild_id, channel_id, player)
        )""")
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel_youtube (
            guild_id INTEGER,
            channel_id INTEGER,
            youtube_channel_id TEXT,
            youtube_channel_name TEXT,
            PRIMARY KEY (guild_id, channel_id, youtube_channel_id)
        )""")
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel_videos (
            guild_id INTEGER,
            channel_id INTEGER,
            video_id TEXT,
            title TEXT,
            url TEXT,
            published_at TEXT,
            PRIMARY KEY (guild_id, channel_id, video_id)
        )""")
        self.conn.commit()
        
    def add_channel(self, guild_id, channel_id, enforce_character_1=False, enforce_character_2=False, enforce_player_1=True, enforce_player_2=True):
        """Add a new channel to the database."""
        self.cursor.execute("""
        INSERT OR IGNORE INTO channels (guild_id, channel_id, enforce_character_1, enforce_character_2, enforce_player_1, enforce_player_2)
        VALUES (?, ?, ?, ?, ?, ?)""", (guild_id, channel_id, enforce_character_1, enforce_character_2, enforce_player_1, enforce_player_2))
        self.conn.commit()
        
    def remove_channel(self, guild_id, channel_id):
        """Remove a channel from the database."""
        self.cursor.execute("""
        DELETE FROM channels WHERE guild_id = ? AND channel_id = ?""", (guild_id, channel_id))
        self.cursor.execute("""
        DELETE FROM channel_characters_1 WHERE guild_id = ? AND channel_id = ?""", (guild_id, channel_id))
        self.cursor.execute("""
        DELETE FROM channel_characters_2 WHERE guild_id = ? AND channel_id = ?""", (guild_id, channel_id))
        self.cursor.execute("""
        DELETE FROM channel_players_1 WHERE guild_id = ? AND channel_id = ?""", (guild_id, channel_id))
        self.cursor.execute("""
        DELETE FROM channel_players_2 WHERE guild_id = ? AND channel_id = ?""", (guild_id, channel_id))
        self.cursor.execute("""
        DELETE FROM channel_youtube WHERE guild_id = ? AND channel_id = ?""", (guild_id, channel_id))
        self.cursor.execute("""
        DELETE FROM channel_videos WHERE guild_id = ? AND channel_id = ?""", (guild_id, channel_id))
        self.conn.commit()
        
    def set_enforce_character_1(self, guild_id, channel_id, enforce):
        """Set the enforce_character_1 flag for a channel."""
        self.cursor.execute("""
        UPDATE channels SET enforce_character_1 = ? WHERE guild_id = ? AND channel_id = ?""", (enforce, guild_id, channel_id))
        self.conn.commit()
        
    def set_enforce_character_2(self, guild_id, channel_id, enforce):
        """Set the enforce_character_2 flag for a channel."""
        self.cursor.execute("""
        UPDATE channels SET enforce_character_2 = ? WHERE guild_id = ? AND channel_id = ?""", (enforce, guild_id, channel_id))
        self.conn.commit()
        
    def set_enforce_player_1(self, guild_id, channel_id, enforce):
        """Set the enforce_player_1 flag for a channel."""
        self.cursor.execute("""
        UPDATE channels SET enforce_player_1 = ? WHERE guild_id = ? AND channel_id = ?""", (enforce, guild_id, channel_id))
        self.conn.commit()
        
    def set_enforce_player_2(self, guild_id, channel_id, enforce):
        """Set the enforce_player_2 flag for a channel."""
        self.cursor.execute("""
        UPDATE channels SET enforce_player_2 = ? WHERE guild_id = ? AND channel_id = ?""", (enforce, guild_id, channel_id))
        self.conn.commit()
        
    def add_character_1(self, guild_id, channel_id, character):
        """Add a character to a channel."""
        self.cursor.execute("""
        INSERT OR IGNORE INTO channel_characters_1 (guild_id, channel_id, characters)
        VALUES (?, ?, ?)""", (guild_id, channel_id, character))
        self.conn.commit()
    
    def add_character_2(self, guild_id, channel_id, character):
        """Add a character to a channel."""
        self.cursor.execute("""
        INSERT OR IGNORE INTO channel_characters_2 (guild_id, channel_id, characters)
        VALUES (?, ?, ?)""", (guild_id, channel_id, character))
        self.conn.commit()
        
    def remove_character_1(self, guild_id, channel_id, character):
        """Remove a character from a channel."""
        self.cursor.execute("""
        DELETE FROM channel_characters_1 WHERE guild_id = ? AND channel_id = ? AND characters = ?""", (guild_id, channel_id, character))
        self.conn.commit()
    
    def remove_character_2(self, guild_id, channel_id, character):
        """Remove a character from a channel."""
        self.cursor.execute("""
        DELETE FROM channel_characters_2 WHERE guild_id = ? AND channel_id = ? AND characters = ?""", (guild_id, channel_id, character))
        self.conn.commit()
    
    def add_player_1(self, guild_id, channel_id, player):
        """Add a player to a channel."""
        self.cursor.execute("""
        INSERT OR IGNORE INTO channel_players_1 (guild_id, channel_id, player)
        VALUES (?, ?, ?)""", (guild_id, channel_id, player))
        self.conn.commit()
        
    def add_player_2(self, guild_id, channel_id, player):
        """Add a player to a channel."""
        self.cursor.execute("""
        INSERT OR IGNORE INTO channel_players_2 (guild_id, channel_id, player)
        VALUES (?, ?, ?)""", (guild_id, channel_id, player))
        self.conn.commit()
        
    def remove_player_1(self, guild_id, channel_id, player):
        """Remove a player from a channel."""
        self.cursor.execute("""
        DELETE FROM channel_players_1 WHERE guild_id = ? AND channel_id = ? AND player = ?""", (guild_id, channel_id, player))
        self.conn.commit()
        
    def remove_player_2(self, guild_id, channel_id, player):
        """Remove a player from a channel."""
        self.cursor.execute("""
        DELETE FROM channel_players_2 WHERE guild_id = ? AND channel_id = ? AND player = ?""", (guild_id, channel_id, player))
        self.conn.commit()
        
    def add_youtube_channel(self, guild_id, channel_id, youtube_channel_id, youtube_channel_name):
        """Add a YouTube channel to a channel."""
        self.cursor.execute("""
        INSERT OR IGNORE INTO channel_youtube (guild_id, channel_id, youtube_channel_id, youtube_channel_name)
        VALUES (?, ?, ?, ?)""", (guild_id, channel_id, youtube_channel_id, youtube_channel_name))
        self.conn.commit()
        
    def remove_youtube_channel(self, guild_id, channel_id, youtube_channel_id):
        """Remove a YouTube channel from a channel."""
        self.cursor.execute("""
        DELETE FROM channel_youtube WHERE guild_id = ? AND channel_id = ? AND youtube_channel_id = ?""", (guild_id, channel_id, youtube_channel_id))
        self.conn.commit()
    
    def add_published(self, guild_id, channel_id, video_id, title, url, published_at):
        """Record that a video was posted to a channel."""
        self.cursor.execute("""
        INSERT OR IGNORE INTO channel_videos (guild_id, channel_id, video_id, title, url, published_at)
        VALUES (?, ?, ?, ?, ?, ?)""", (guild_id, channel_id, video_id, title, url, published_at))
        self.conn.commit()
        
    def remove_published_by_url(self, guild_id, channel_id, video_url):
        """Forget a posted video (by URL) for a channel."""
        self.cursor.execute("""
        DELETE FROM channel_videos WHERE guild_id = ? AND channel_id = ? AND url = ?""", (guild_id, channel_id, video_url))
        self.conn.commit()
    
    def get_published(self, guild_id, channel_id):
        """Get the videos already posted to a channel."""
        self.cursor.execute("""
        SELECT video_id, title, url, published_at FROM channel_videos
        WHERE guild_id = ? AND channel_id = ?""", (guild_id, channel_id))
        return self.cursor.fetchall()
    
    def clear_guild_database(self, guild_id):
        """Clear all data for a guild."""
        self.cursor.execute("""
        DELETE FROM channels WHERE guild_id = ?""", (guild_id,))
        self.cursor.execute("""
        DELETE FROM channel_characters_1 WHERE guild_id = ?""", (guild_id,))
        self.cursor.execute("""
        DELETE FROM channel_characters_2 WHERE guild_id = ?""", (guild_id,))
        self.cursor.execute("""
        DELETE FROM channel_players_1 WHERE guild_id = ?""", (guild_id,))
        self.cursor.execute("""
        DELETE FROM channel_players_2 WHERE guild_id = ?""", (guild_id,))
        self.cursor.execute("""
        DELETE FROM channel_youtube WHERE guild_id = ?""", (guild_id,))
        self.cursor.execute("""
        DELETE FROM channel_videos WHERE guild_id = ?""", (guild_id,))
        self.conn.commit()
    
    def load_guild_config(self, guild_id):
        """Load all channels and their config for a guild in one go."""
        # Load channels + enforce flag
        self.cursor.execute("SELECT channel_id, enforce_character_1, enforce_character_2, enforce_player_1, enforce_player_2 FROM channels WHERE guild_id=?", (guild_id,))
        channels = {row["channel_id"]: {"enforce_character_1": bool(row["enforce_character_1"]),
                                        "enforce_character_2": bool(row["enforce_character_2"]),
                                        "enforce_player_1": bool(row["enforce_player_1"]),
                                        "enforce_player_2": bool(row["enforce_player_2"]),
                                        "characters_1": [],
                                        "characters_2": [],
                                        "players_1": [],
                                        "players_2": [],
                                        "youtube_channels": {}}
                    for row in self.cursor.fetchall()}

        if not channels:
            return {}

        channel_ids = tuple(channels.keys())

        # Load characters_1
        self.cursor.execute(f"""
            SELECT channel_id, characters FROM channel_characters_1
            WHERE guild_id=? AND channel_id IN ({','.join('?' for _ in channel_ids)})
        """, (guild_id, *channel_ids))
        for row in self.cursor.fetchall():
            channels[row["channel_id"]]["characters_1"].append(row["characters"])

        # Load characters_2
        self.cursor.execute(f"""
            SELECT channel_id, characters FROM channel_characters_2
            WHERE guild_id=? AND channel_id IN ({','.join('?' for _ in channel_ids)})
        """, (guild_id, *channel_ids))
        for row in self.cursor.fetchall():
            channels[row["channel_id"]]["characters_2"].append(row["characters"])

        # Load players_1
        self.cursor.execute(f"""
            SELECT channel_id, player FROM channel_players_1
            WHERE guild_id=? AND channel_id IN ({','.join('?' for _ in channel_ids)})
        """, (guild_id, *channel_ids))
        for row in self.cursor.fetchall():
            channels[row["channel_id"]]["players_1"].append(row["player"])

        # Load players_2
        self.cursor.execute(f"""
            SELECT channel_id, player FROM channel_players_2
            WHERE guild_id=? AND channel_id IN ({','.join('?' for _ in channel_ids)})
        """, (guild_id, *channel_ids))
        for row in self.cursor.fetchall():
            channels[row["channel_id"]]["players_2"].append(row["player"])

        # Load YouTube channels
        self.cursor.execute(f"""
            SELECT channel_id, youtube_channel_id, youtube_channel_name FROM channel_youtube
            WHERE guild_id=? AND channel_id IN ({','.join('?' for _ in channel_ids)})
        """, (guild_id, *channel_ids))
        for row in self.cursor.fetchall():
            channels[row["channel_id"]]["youtube_channels"][row["youtube_channel_name"]] = row["youtube_channel_id"]

        return channels

        