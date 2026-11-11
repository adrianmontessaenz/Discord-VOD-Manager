import json
import os
from filters import ChannelFilter
from repositories import SqliteGuildSettingsRepository, YggdrasilError
from vod_sync import ChannelTarget

smash_characters={}


def _read_config_file() -> dict:
    if os.path.exists('data/config.json'):
        with open('data/config.json', 'r', encoding='utf-8') as file:
            return json.load(file)
    return {}


def char_aliases() -> dict:
    """Character translations from data/config.json["char_names"]: {english name: (translations...)}."""
    return {name: tuple(names) for name, names in _read_config_file().get("char_names", {}).items()}

class _MyChannels:
    """
    This class is used to store the configuration for each channel. 
    It contains the list of characters, players and youtube channels to search for in the videos.
    """
    def __init__(self):
        """Initialize the configuration for a channel. 
        It will load the youtube channels from the config file if it exists, otherwise it will start with an empty list."""
        file_json = _read_config_file()

        self.characters_1 = []
        self.characters_2 = []
        self.enforce_character_1 = False
        self.enforce_character_2 = False
        self.players_1 = []
        self.players_2 = []
        self.enforce_player_1 = True
        self.enforce_player_2 = True
        self.youtube_channels = dict(file_json.get("youtube_channels", {}))  # {name: id}, own copy

class MyConfig:
    def __init__(self):
        """Initialize the configuration for all channels."""
        self._my_channels = {}
        
    def _add_new_channel(self, id: int, guild_id: int, database: SqliteGuildSettingsRepository = None):
        """Add a new channel to the configuration. 
        It will create a new instance of _MyChannels for the channel and store it in the dictionary.

        Args:
            id (int): The ID of the channel.
        """
        self._my_channels[id] = _MyChannels()
        if database is not None:
            database.add_channel(guild_id, id, self._my_channels[id].enforce_character_1, self._my_channels[id].enforce_character_2, self._my_channels[id].enforce_player_1, self._my_channels[id].enforce_player_2)
            for yt in self._my_channels[id].youtube_channels:
                database.add_youtube_channel(guild_id, id, self._my_channels[id].youtube_channels[yt], yt)
        
    def add_channel(self, id: int, characters_1: list, characters_2: list, players_1: list, players_2: list, youtube_channels: list, enforce_variables: dict):
        """Add a channel to the configuration. 
        It will create a new instance of _MyChannels for the channel and store it in the dictionary.

        Args:
            id (int): The ID of the channel.
            characters_1 (list): The list of characters to search for in the videos for player 1.
            characters_2 (list): The list of characters to search for in the videos for player 2.
            players_1 (list): The list of players to search for in the videos for player 1.
            players_2 (list): The list of players to search for in the videos for player 2.
            youtube_channels (list): The list of YouTube channels to search for videos.
            enforce_variables (dict): Whether to enforce that the characters are also in the title of the videos.
        """
        self._my_channels[id] = _MyChannels()
        self._my_channels[id].characters_1 = characters_1
        self._my_channels[id].characters_2 = characters_2
        self._my_channels[id].players_1 = players_1
        self._my_channels[id].players_2 = players_2
        self._my_channels[id].enforce_character_1 = enforce_variables["enforce_character_1"] if "enforce_character_1" in enforce_variables else False
        self._my_channels[id].enforce_character_2 = enforce_variables["enforce_character_2"] if "enforce_character_2" in enforce_variables else False
        self._my_channels[id].enforce_player_1 = enforce_variables["enforce_player_1"] if "enforce_player_1" in enforce_variables else True
        self._my_channels[id].enforce_player_2 = enforce_variables["enforce_player_2"] if "enforce_player_2" in enforce_variables else True
        self._my_channels[id].youtube_channels = youtube_channels
    
    def remove_channel(self, guild_id: int, id: int, database: SqliteGuildSettingsRepository = None):
        """Remove a channel from the configuration. 
        It will remove the instance of _MyChannels for the channel from the dictionary.

        Args:
            id (int): The ID of the channel.
        """
        if id in self._my_channels.keys():
            self._my_channels.pop(id)
            database.remove_channel(guild_id, id)
            
    def add_character_1(self, guild_id: int, id: int, char: str, database: SqliteGuildSettingsRepository = None):
        """Add a character to the list of characters to search for in the videos.

        Args:
            id (int): The ID of the channel.
            char (str): The character to add.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
            
        if char in self._my_channels[id].characters_1:
            return f"Character '{char}' was already stored"
        self._my_channels[id].characters_1.append(char)
        database.add_character_1(guild_id, id, char)
        return f"Character '{char}' was stored"
    
    def add_character_2(self, guild_id: int, id: int, char: str, database: SqliteGuildSettingsRepository = None):
        """Add a character to the list of characters to search for in the videos.

        Args:
            id (int): The ID of the channel.
            char (str): The character to add.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
            
        if char in self._my_channels[id].characters_2:
            return f"Character '{char}' was already stored"
        self._my_channels[id].characters_2.append(char)
        database.add_character_2(guild_id, id, char)
        return f"Character '{char}' was stored"
        
    def remove_character_1(self, guild_id: int, id: int, char: str, database: SqliteGuildSettingsRepository = None):
        """Remove a character from the list of characters to search for in the videos.

        Args:
            id (int): The ID of the channel.
            char (str): The character to remove.

        Returns:
            _type_: The result of the operation.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        if char in self._my_channels[id].characters_1:
            self._my_channels[id].characters_1.remove(char)
            database.remove_character_1(guild_id, id, char)
            return f"Character '{char}' was removed from search"
        return f"Character '{char}' was not found in search"
            
    def remove_character_2(self, guild_id: int, id: int, char: str, database: SqliteGuildSettingsRepository = None):
        """Remove a character from the list of characters to search for in the videos.

        Args:
            id (int): The ID of the channel.
            char (str): The character to remove.
        Returns:
            _type_: The result of the operation.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        if char in self._my_channels[id].characters_2:
            self._my_channels[id].characters_2.remove(char)
            database.remove_character_2(guild_id, id, char)
            return f"Character '{char}' was removed from search"
        return f"Character '{char}' was not found in search"
            
    def get_characters_1(self, guild_id: int, id: int, database: SqliteGuildSettingsRepository = None):
        """Get the list of characters to search for in the videos for a specific channel.

        Args:
            id (int): The ID of the channel.

        Returns:
            _type_: The list of characters for the specified channel.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        return self._my_channels[id].characters_1
    
    def get_characters_2(self, guild_id: int, id: int, database: SqliteGuildSettingsRepository = None):
        """Get the list of characters to search for in the videos for a specific channel.

        Args:
            id (int): The ID of the channel.

        Returns:
            _type_: The list of characters for the specified channel.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        return self._my_channels[id].characters_2
    
    def enforce_character_1(self, guild_id: int, id:int, state: bool, database: SqliteGuildSettingsRepository = None):
        """Set the enforce_characters flag for a specific channel. 
        This flag is used to determine if the bot should enforce that the characters are also in the title of the videos.
         

        Args:
            id (int): The ID of the channel.
            state (bool): The state to set the flag to.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        self._my_channels[id].enforce_character_1 = state
        database.set_enforce_character_1(guild_id, id, state)
    
        
    def enforce_character_2(self, guild_id: int, id:int, state: bool, database: SqliteGuildSettingsRepository = None):
        """Set the enforce_characters flag for a specific channel. 
        This flag is used to determine if the bot should enforce that the characters are also in the title of the videos.
         

        Args:
            id (int): The ID of the channel.
            state (bool): The state to set the flag to.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        self._my_channels[id].enforce_character_2 = state
        database.set_enforce_character_2(guild_id, id, state)

    def set_enforce_characters(self, guild_id: int, id: int, state: bool, database: SqliteGuildSettingsRepository = None):
        """Shortcut: set both enforce_character_1 and enforce_character_2."""
        self.enforce_character_1(guild_id, id, state, database)
        self.enforce_character_2(guild_id, id, state, database)

    def get_filter(self, guild_id: int, id: int, database: SqliteGuildSettingsRepository = None) -> ChannelFilter:
        """Build the ChannelFilter of a text channel from its stored configuration."""
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        c = self._my_channels[id]
        return ChannelFilter(
            players_1=tuple(c.players_1), players_2=tuple(c.players_2),
            characters_1=tuple(c.characters_1), characters_2=tuple(c.characters_2),
            enforce_player_1=c.enforce_player_1, enforce_player_2=c.enforce_player_2,
            enforce_character_1=c.enforce_character_1, enforce_character_2=c.enforce_character_2)

    def uses_youtube_channel(self, channel_id: str) -> bool:
        """True if any text channel of this guild stores this YouTube channel id."""
        return any(channel_id in c.youtube_channels.values() for c in self._my_channels.values())

    def all_youtube_channels(self) -> dict:
        """{name: channel_id} for every YouTube channel stored in this guild."""
        result = {}
        for c in self._my_channels.values():
            result.update(c.youtube_channels)
        return result

    def _known_name_for_id(self, channel_id: str):
        """Name under which any local text channel already stores this YouTube channel id."""
        for channel in self._my_channels.values():
            for name, known_id in channel.youtube_channels.items():
                if known_id == channel_id:
                    return name
        return None

    def add_youtube_channel(self, guild_id: int, id: int, yt: str, sources, database: SqliteGuildSettingsRepository = None):
        """Add a YouTube channel to this text channel and register it in Yggdrasil.
         You can add a channel by its ID (starting with UC) or by its @handle.

        Args:
            id (int): The ID of the Discord text channel.
            yt (str): The YouTube channel ID or @handle.
            sources: A YggdrasilClient (or None when Yggdrasil is not configured).

        Returns:
            str: The result of the operation.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        local = self._my_channels[id].youtube_channels
        if not (yt.startswith("UC") or yt.startswith("@")):
            return f"Invalid channel format '{yt}'. Please provide a channel ID starting with 'UC' or a channel name starting with '@'"
        if yt.startswith("UC") and yt in local.values():
            return f"Channel '{yt}' was already stored"
        if sources is None:
            return "Could not register the channel in Yggdrasil: Yggdrasil is not configured"

        known_name = self._known_name_for_id(yt) if yt.startswith("UC") else None
        try:
            info = sources.add_source(yt, name=known_name) if known_name else sources.add_source(yt)
        except YggdrasilError as error:
            return f"Could not register the channel in Yggdrasil: {error}"
        channel_id, name = info["channel_id"], info["name"]
        if channel_id in local.values():
            return f"Channel '{yt}' was already stored"

        local[name] = channel_id
        database.add_youtube_channel(guild_id, id, channel_id, name)
        try:
            sources.request_history(channel_id)
        except YggdrasilError:
            pass  # best effort: the history can be requested again later
        return f"Channel '{yt}' was stored"

    def remove_youtube_channel(self, guild_id: int, id: int, yt: str, database: SqliteGuildSettingsRepository = None,
                               sources=None, other_users=None):
        """Remove a YouTube channel (by name or id) from this text channel.
        It is removed from Yggdrasil only when no other local text channel still uses it.

        Args:
            other_users: callable(channel_id) -> bool, True if another local text channel uses the channel.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        local = self._my_channels[id].youtube_channels
        if yt not in local:
            by_id = [name for name, known_id in local.items() if known_id == yt]
            if not by_id:
                return f"Channel '{yt}' was not found in search"
            yt = by_id[0]
        channel_id = local[yt]  # read before popping
        local.pop(yt)
        database.remove_youtube_channel(guild_id, id, channel_id)
        if sources is not None and not (other_users and other_users(channel_id)):
            try:
                sources.remove_source(channel_id)
            except YggdrasilError:
                pass  # local removal stands; Yggdrasil keeps watching until the next removal
        return f"Channel '{yt}' was removed from search"

    def list_youtube_channels(self, guild_id: int, id: int, database: SqliteGuildSettingsRepository = None, sources=None):
        """[(name, id, watched_by_yggdrasil)]. Everything counts as watched when Yggdrasil cannot be asked."""
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        local = self._my_channels[id].youtube_channels
        watched = None
        if sources is not None:
            try:
                watched = {s["channel_id"] for s in sources.list_sources()}
            except YggdrasilError:
                watched = None
        return [(name, cid, watched is None or cid in watched) for name, cid in local.items()]

    def targets(self, guild_id: int, auto_channel_ids, database: SqliteGuildSettingsRepository = None):
        """ChannelTargets for the given Discord text channels of a guild."""
        result = []
        for channel_id in auto_channel_ids:
            if channel_id not in self._my_channels.keys():
                self._add_new_channel(channel_id, guild_id, database)
            ids = frozenset(self._my_channels[channel_id].youtube_channels.values())
            result.append(ChannelTarget(guild_id, channel_id, ids,
                                        self.get_filter(guild_id, channel_id, database)))
        return result
        
    def get_youtube_channels(self, guild_id: int, id: int, database: SqliteGuildSettingsRepository = None):
        """Get the list of YouTube channels for a specific channel.

        Args:
            id (int): The ID of the channel.

        Returns:
            _type_: The list of YouTube channel IDs for the specified channel.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        return self._my_channels[id].youtube_channels.keys()

    def add_player_1(self, guild_id: int, id: int, player: str, database: SqliteGuildSettingsRepository = None):
        """Add a player to the list of players for a specific channel.

        Args:
            id (int): The ID of the channel.
            player (str): The name of the player to add.

        Returns:
            _type_: The result of the operation.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        if player in self._my_channels[id].players_1:
            return f"Player '{player}' was already stored"
        self._my_channels[id].players_1.append(player)
        database.add_player_1(guild_id, id, player)
        return f"Player '{player}' was stored"
        
    def add_player_2(self, guild_id: int, id: int, player: str, database: SqliteGuildSettingsRepository = None):
        """Add a player to the list of players for a specific channel.

        Args:
            id (int): The ID of the channel.
            player (str): The name of the player to add.
        Returns:
            _type_: The result of the operation.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        if player in self._my_channels[id].players_2:
            return f"Player '{player}' was already stored"
        self._my_channels[id].players_2.append(player)
        database.add_player_2(guild_id, id, player)
        return f"Player '{player}' was stored"
    
    def remove_player_1(self, guild_id: int, id: int, player: str, database: SqliteGuildSettingsRepository = None):
        """Remove a player from the list of players for a specific channel.

        Args:
            id (int): The ID of the channel.
            player (str): The name of the player to remove.

        Returns:
            _type_: The result of the operation.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        if player in self._my_channels[id].players_1:
            self._my_channels[id].players_1.remove(player)
            database.remove_player_1(guild_id, id, player)
            return f"Player '{player}' was removed from search"
        return f"Player '{player}' was not found in search"
    
    def remove_player_2(self, guild_id: int, id: int, player: str, database: SqliteGuildSettingsRepository = None):
        """Remove a player from the list of players for a specific channel.

        Args:
            id (int): The ID of the channel.
            player (str): The name of the player to remove.
        Returns:
            _type_: The result of the operation.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        if player in self._my_channels[id].players_2:
            self._my_channels[id].players_2.remove(player)
            database.remove_player_2(guild_id, id, player)
            return f"Player '{player}' was removed from search"
        return f"Player '{player}' was not found in search"
    
    def enforce_player_1(self, guild_id: int, id:int, state: bool, database: SqliteGuildSettingsRepository = None):
        """Set the enforce_player_1 flag for a specific channel. 
        This flag is used to determine if the bot should enforce that player 1 is also in the title of the videos.
         

        Args:
            id (int): The ID of the channel.
            state (bool): The state to set the flag to.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        self._my_channels[id].enforce_player_1 = state
        database.set_enforce_player_1(guild_id, id, state)
        
    def enforce_player_2(self, guild_id: int, id:int, state: bool, database: SqliteGuildSettingsRepository = None):
        """Set the enforce_player_2 flag for a specific channel. 
        This flag is used to determine if the bot should enforce that player 2 is also in the title of the videos.
         

        Args:
            id (int): The ID of the channel.
            state (bool): The state to set the flag to.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        self._my_channels[id].enforce_player_2 = state
        database.set_enforce_player_2(guild_id, id, state)
            
    def get_players_1(self, guild_id: int, id: int, database: SqliteGuildSettingsRepository = None):
        """Get the list of players for a specific channel.

        Args:
            id (int): The ID of the channel.

        Returns:
            _type_: The list of players for the specified channel.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        return self._my_channels[id].players_1
    
    def get_players_2(self, guild_id: int, id: int, database: SqliteGuildSettingsRepository = None):
        """Get the list of players for a specific channel.

        Args:
            id (int): The ID of the channel.

        Returns:
            _type_: The list of players for the specified channel.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        return self._my_channels[id].players_2
