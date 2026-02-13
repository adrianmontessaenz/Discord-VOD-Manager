from datetime import datetime, timezone
import json
import os
import sqlite3
import database

smash_characters={}

class _MyChannels:
    """
    This class is used to store the configuration for each channel. 
    It contains the list of characters, players and youtube channels to search for in the videos.
    """
    def __init__(self):
        """Initialize the configuration for a channel. 
        It will load the youtube channels from the config file if it exists, otherwise it will start with an empty list."""
        file_json = {}
        if os.path.exists('data/config.json'):
            with open('data/config.json', 'r') as file:
                file_json = json.load(file)
        
        self.characters_1 = []
        self.characters_2 = []
        self.players_1 = []
        self.players_2 = []
        self.youtube_channels = file_json["youtube_channels"]
        self.enforce_characters = True

class MyConfig:
    def __init__(self):
        """Initialize the configuration for all channels."""
        self._my_channels = {}
        
    def _add_new_channel(self, id: int, guild_id: int, database: database.MyDatabase = None):
        """Add a new channel to the configuration. 
        It will create a new instance of _MyChannels for the channel and store it in the dictionary.

        Args:
            id (int): The ID of the channel.
        """
        self._my_channels[id] = _MyChannels()
        if database is not None:
            database.add_channel(guild_id, id)
            for yt in self._my_channels[id].youtube_channels:
                database.add_youtube_channel(guild_id, id, self._my_channels[id].youtube_channels[yt], yt)
        
    def add_channel(self, id: int, characters_1: list, characters_2: list, players_1: list, players_2: list, youtube_channels: list, enforce_characters: bool):
        """Add a channel to the configuration. 
        It will create a new instance of _MyChannels for the channel and store it in the dictionary.

        Args:
            id (int): The ID of the channel.
            characters_1 (list): The list of characters to search for in the videos for player 1.
            characters_2 (list): The list of characters to search for in the videos for player 2.
            players_1 (list): The list of players to search for in the videos for player 1.
            players_2 (list): The list of players to search for in the videos for player 2.
            youtube_channels (list): The list of YouTube channels to search for videos.
            enforce_characters (bool): Whether to enforce that the characters are also in the title of the videos.
        """
        self._my_channels[id] = _MyChannels()
        self._my_channels[id].characters_1 = characters_1
        self._my_channels[id].characters_2 = characters_2
        self._my_channels[id].players_1 = players_1
        self._my_channels[id].players_2 = players_2
        self._my_channels[id].enforce_characters = enforce_characters
        self._my_channels[id].youtube_channels = youtube_channels
    
    def remove_channel(self, guild_id: int, id: int, database: database.MyDatabase = None):
        """Remove a channel from the configuration. 
        It will remove the instance of _MyChannels for the channel from the dictionary.

        Args:
            id (int): The ID of the channel.
        """
        if id in self._my_channels.keys():
            self._my_channels.pop(id)
            database.remove_channel(guild_id, id)
            
    def add_character_1(self, guild_id: int, id: int, char: str, database: database.MyDatabase = None):
        """Add a character to the list of characters to search for in the videos.

        Args:
            id (int): The ID of the channel.
            char (str): The character to add.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        self._my_channels[id].characters_1.append(char)
        database.add_character_1(guild_id, id, char)
    
    def add_character_2(self, guild_id: int, id: int, char: str, database: database.MyDatabase = None):
        """Add a character to the list of characters to search for in the videos.

        Args:
            id (int): The ID of the channel.
            char (str): The character to add.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        self._my_channels[id].characters_2.append(char)
        database.add_character_2(guild_id, id, char)
        
    def remove_character_1(self, guild_id: int, id: int, char: str, database: database.MyDatabase = None):
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
            
    def remove_character_2(self, guild_id: int, id: int, char: str, database: database.MyDatabase = None):
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
            
    def get_characters_1(self, guild_id: int, id: int, database: database.MyDatabase = None):
        """Get the list of characters to search for in the videos for a specific channel.

        Args:
            id (int): The ID of the channel.

        Returns:
            _type_: The list of characters for the specified channel.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        return self._my_channels[id].characters_1
    
    def get_characters_2(self, guild_id: int, id: int, database: database.MyDatabase = None):
        """Get the list of characters to search for in the videos for a specific channel.

        Args:
            id (int): The ID of the channel.

        Returns:
            _type_: The list of characters for the specified channel.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        return self._my_channels[id].characters_2
        
    def enforce_characters(self, guild_id: int, id:int, state: bool, database: database.MyDatabase = None):
        """Set the enforce_characters flag for a specific channel. 
        This flag is used to determine if the bot should enforce that the characters are also in the title of the videos.
         

        Args:
            id (int): The ID of the channel.
            state (bool): The state to set the flag to.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        self._my_channels[id].enforce_characters = state
        database.set_enforce_character(guild_id, id, state)
        
    def add_youtube_channel(self, guild_id: int, id: int, yt: str, youtube, database: database.MyDatabase = None):
        """Add a youtube channel to the list of channels to search for videos.
         You can add a channel by its ID (starting with UC) or by its @name. 
         If you add it by @name, the bot will search for the channel and add it if it finds it.

        Args:
            id (int): The ID of the channel.
            yt (str): The YouTube channel ID or @name.
            youtube (_type_): The YouTube API object.

        Returns:
            _type_: The result of the operation.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        if yt.startswith("UC"):
            if yt in self._my_channels[id].youtube_channels:
                return f"Channel '{yt} was already stored"
            self._my_channels[id].youtube_channels.append(yt)
            return f"Channel '{yt}' was stored"
        elif yt.startswith("@"):
            yt = yt[1:]
        
        res = youtube.search().list(
            part="snippet",
            q=yt,
            type="channel",
            maxResults=1
        ).execute()
        
        items = res.get("items")
        if not items:
            return f"Channel '{yt}' not found"
        
        if items[0]["snippet"]["channelId"] in self._my_channels[id].youtube_channels:
            return f"Channel '{yt} was already stored"
        
        self._my_channels[id].youtube_channels[items[0]["snippet"]["title"]] = items[0]["snippet"]["channelId"]
        database.add_youtube_channel(guild_id, id, items[0]["snippet"]["channelId"], items[0]["snippet"]["title"])
        return f"Channel '{yt}' was stored"
    
    def remove_youtube_channel(self, guild_id: int, id: int, yt: str, database: database.MyDatabase = None):
        """Remove a youtube channel from the list of channels to search for videos.

        Args:
            id (int): The ID of the channel.
            yt (str): The YouTube channel ID or @name.

        Returns:
            _type_: The result of the operation.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        if yt in self._my_channels[id].youtube_channels.keys():
            self._my_channels[id].youtube_channels.pop(yt)
            database.remove_youtube_channel(guild_id, id, self._my_channels[id].youtube_channels[yt])
            return f"Channel '{yt}' was removed from search"
        return f"Channel '{yt}' was not found in search"
        
    def get_youtube_channels(self, guild_id: int, id: int, database: database.MyDatabase = None):
        """Get the list of YouTube channels for a specific channel.

        Args:
            id (int): The ID of the channel.

        Returns:
            _type_: The list of YouTube channel IDs for the specified channel.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        return self._my_channels[id].youtube_channels.keys()

    def add_player_1(self, guild_id: int, id: int, player: str, database: database.MyDatabase = None):
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
        
    def add_player_2(self, guild_id: int, id: int, player: str, database: database.MyDatabase = None):
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
    
    def remove_player_1(self, guild_id: int, id: int, player: str, database: database.MyDatabase = None):
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
    
    def remove_player_2(self, guild_id: int, id: int, player: str, database: database.MyDatabase = None):
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
            
    def get_players_1(self, guild_id: int, id: int, database: database.MyDatabase = None):
        """Get the list of players for a specific channel.

        Args:
            id (int): The ID of the channel.

        Returns:
            _type_: The list of players for the specified channel.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        return self._my_channels[id].players_1
    
    def get_players_2(self, guild_id: int, id: int, database: database.MyDatabase = None):
        """Get the list of players for a specific channel.

        Args:
            id (int): The ID of the channel.

        Returns:
            _type_: The list of players for the specified channel.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        return self._my_channels[id].players_2
    
    def get_old_videos(self, guild_id: int, id: int, youtube, date: str = None, database: database.MyDatabase = None):
        """Get old videos for a specific channel.

        Args:
            id (int): The ID of the channel.
            youtube (_type_): The YouTube API client.
            date (str, optional): The date to filter videos by. Only videos published after this date will be returned. Should be in the format 'YYYY-MM-DD'. Defaults to None, which means no date filtering.

        Returns:
            _type_: The list of old videos for the specified channel.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id, guild_id, database)
        all_videos = []
        
        # Parse date if provided. If provided wrong, print error and ignore date filter
        filter_date = None
        if date is not None:
            try:
                filter_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                print(f"Invalid date format '{date}'. Expected format is 'YYYY-MM-DD'")
                return [{"error": f"Invalid date format '{date}'. Expected format is 'YYYY-MM-DD'"}]

        # Loop on youtube channels
        for youtube_channel in self._my_channels[id].youtube_channels:
            print(f"Getting videos for channel '{youtube_channel}'")
            # Get uploads playlist
            res =  youtube.channels().list(
                part="contentDetails",
                id=self._my_channels[id].youtube_channels[youtube_channel]
            ).execute()
            
            items = res.get("items")
            uploads_playlist_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
            next_page_token = None
            
            # Loop on videos
            loopCheck = True
            while loopCheck:
                res = youtube.playlistItems().list(
                    part="snippet",
                    playlistId=uploads_playlist_id,
                    maxResults=25,
                    pageToken=next_page_token
                ).execute()                
                
                # For each video in page, check if its valid following criteria
                for video in res.get("items", []):
                    video_id = video["snippet"]["resourceId"]["videoId"]
                    title = video["snippet"]["title"]
                    url = f"https://www.youtube.com/watch?v={video_id}"
                    published_at = video["snippet"]["publishedAt"]  # ISO 8601 string
                 
                    # Convert to datetime
                    dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))

                    #
                    # Check if older than 2019 or filter date, if so stop the loop
                    if dt.year < 2019 or filter_date is not None and dt < filter_date:
                        loopCheck = False
                        break  # stop the loop entirely
                    
                    has_character_1 = False
                    has_character_2 = False
                    has_player_1 = False
                    has_player_2 = False
                    
                    # Check character names
                    if len(self._my_channels[id].characters_1) >= 1:
                        for char in self._my_channels[id].characters_1:
                            if char in title:
                                print(f"Video '{title}' has character '{char}' in it")
                                has_character_1 = True
                                break
                    else:
                        has_character_1 = True
                        
                    # Check character names
                    if len(self._my_channels[id].characters_2) >= 1:
                        for char in self._my_channels[id].characters_2:
                            if char in title:
                                print(f"Video '{title}' has character '{char}' in it")
                                has_character_2 = True
                                break
                    else:
                        has_character_2 = True
                        
                    # Check player names
                    if len(self._my_channels[id].players_1) >= 1:
                        for player in self._my_channels[id].players_1:
                            if player in title:
                                print(f"Video '{title}' has player1 '{player}' in it")
                                has_player_1 = True
                                break
                    else:
                        has_player_1 = True
                    
                    # Check player names
                    if len(self._my_channels[id].players_2) >= 1:
                        for player in self._my_channels[id].players_2:
                            if player in title:
                                print(f"Video '{title}' has player2 '{player}' in it")
                                has_player_2 = True
                                break
                    else:
                        has_player_2 = True
                    
                    # Check if video is valid
                    if has_player_1 is True and has_player_2 is True and ((has_character_1 is True and has_character_2 is True) or self._my_channels[id].enforce_characters is False): 
                        print(f"Video '{title}' passed all criteria, adding it to the list")
                        all_videos.append(
                            {
                                "title": title,
                                "url": url,
                                "publishedAt": published_at
                            })
                
                # Skip to next page of videos
                next_page_token = res.get("nextPageToken")
                if not next_page_token:
                    break
        
        # Sort all videos from oldest to latest
        all_videos.sort(key=lambda v: datetime.fromisoformat(v['publishedAt'].replace("Z", "+00:00")))
        return all_videos

                        


        
        
        
