from datetime import datetime
import json
import os

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
        if os.path.exist('data/config.json'):
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
        
    def _add_new_channel(self, id: int):
        """Add a new channel to the configuration. 
        It will create a new instance of _MyChannels for the channel and store it in the dictionary.

        Args:
            id (int): The ID of the channel.
        """
        self._my_channels[id] = _MyChannels()
    
    def add_character_1(self, id: int, char: str):
        """Add a character to the list of characters to search for in the videos.

        Args:
            id (int): The ID of the channel.
            char (str): The character to add.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id)
        self._my_channels[id].characters_1.append(char)
    
    def add_character_2(self, id: int, char: str):
        """Add a character to the list of characters to search for in the videos.

        Args:
            id (int): The ID of the channel.
            char (str): The character to add.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id)
        self._my_channels[id].characters_2.append(char)
        
    def remove_character_1(self, id: int, char: str):
        """Remove a character from the list of characters to search for in the videos.

        Args:
            id (int): The ID of the channel.
            char (str): The character to remove.

        Returns:
            _type_: The result of the operation.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id)
        if char in self._my_channels[id].characters_1:
            self._my_channels[id].characters_1.remove(char)
            return f"Character '{char}' was removed from search"
        return f"Character '{char}' was not found in search"
            
    def remove_character_2(self, id: int, char: str):
        """Remove a character from the list of characters to search for in the videos.

        Args:
            id (int): The ID of the channel.
            char (str): The character to remove.
        Returns:
            _type_: The result of the operation.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id)
        if char in self._my_channels[id].characters_2:
            self._my_channels[id].characters_2.remove(char)
            return f"Character '{char}' was removed from search"
        return f"Character '{char}' was not found in search"
            
    def get_characters_1(self, id: int):
        """Get the list of characters to search for in the videos for a specific channel.

        Args:
            id (int): The ID of the channel.

        Returns:
            _type_: The list of characters for the specified channel.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id)
        return self._my_channels[id].characters_1
    
    def get_characters_2(self, id: int):
        """Get the list of characters to search for in the videos for a specific channel.

        Args:
            id (int): The ID of the channel.

        Returns:
            _type_: The list of characters for the specified channel.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id)
        return self._my_channels[id].characters_2
        
    def enforce_characters(self, id:int, state: bool):
        """Set the enforce_characters flag for a specific channel. 
        This flag is used to determine if the bot should enforce that the characters are also in the title of the videos.
         

        Args:
            id (int): The ID of the channel.
            state (bool): The state to set the flag to.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id)
        self._my_channels[id].enforce_characters = state
        
    def add_youtube_channel(self, id: int, yt: str, youtube):
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
            self._add_new_channel(id)
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
        return f"Channel '{yt}' was stored"
    
    def remove_youtube_channel(self, id: int, yt: str):
        """Remove a youtube channel from the list of channels to search for videos.

        Args:
            id (int): The ID of the channel.
            yt (str): The YouTube channel ID or @name.

        Returns:
            _type_: The result of the operation.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id)
        if yt in self._my_channels[id].youtube_channels.keys():
            self._my_channels[id].youtube_channels.pop(yt)
            return f"Channel '{yt}' was removed from search"
        return f"Channel '{yt}' was not found in search"
        
    def get_youtube_channels(self, id: int):
        """Get the list of YouTube channels for a specific channel.

        Args:
            id (int): The ID of the channel.

        Returns:
            _type_: The list of YouTube channel IDs for the specified channel.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id)
        return self._my_channels[id].youtube_channels.keys()

    def add_player_1(self, id: int, player: str):
        """Add a player to the list of players for a specific channel.

        Args:
            id (int): The ID of the channel.
            player (str): The name of the player to add.

        Returns:
            _type_: The result of the operation.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id)
        if player in self._my_channels[id].players_1:
            return f"Player '{player}' was already stored"
        self._my_channels[id].players_1.append(player)
        return f"Player '{player}' was stored"
        
    def add_player_2(self, id: int, player: str):
        """Add a player to the list of players for a specific channel.

        Args:
            id (int): The ID of the channel.
            player (str): The name of the player to add.
        Returns:
            _type_: The result of the operation.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id)
        if player in self._my_channels[id].players_2:
            return f"Player '{player}' was already stored"
        self._my_channels[id].players_2.append(player)
        return f"Player '{player}' was stored"
    
    def remove_player_1(self, id: int, player: str):
        """Remove a player from the list of players for a specific channel.

        Args:
            id (int): The ID of the channel.
            player (str): The name of the player to remove.

        Returns:
            _type_: The result of the operation.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id)
        if player in self._my_channels[id].players_1:
            self._my_channels[id].players_1.remove(player)
            return f"Player '{player}' was removed from search"
        return f"Player '{player}' was not found in search"
    
    def remove_player_2(self, id: int, player: str):
        """Remove a player from the list of players for a specific channel.

        Args:
            id (int): The ID of the channel.
            player (str): The name of the player to remove.
        Returns:
            _type_: The result of the operation.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id)
        if player in self._my_channels[id].players_2:
            self._my_channels[id].players_2.remove(player)
            return f"Player '{player}' was removed from search"
        return f"Player '{player}' was not found in search"
            
    def get_players_1(self, id: int):
        """Get the list of players for a specific channel.

        Args:
            id (int): The ID of the channel.

        Returns:
            _type_: The list of players for the specified channel.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id)
        return self._my_channels[id].players_1
    
    def get_players_2(self, id: int):
        """Get the list of players for a specific channel.

        Args:
            id (int): The ID of the channel.

        Returns:
            _type_: The list of players for the specified channel.
        """
        if id not in self._my_channels.keys():
            self._add_new_channel(id)
        return self._my_channels[id].players_2
    
    def get_old_videos(self, id: int, youtube):
        """Get old videos for a specific channel.

        Args:
            id (int): The ID of the channel.
            youtube (_type_): The YouTube API client.

        Returns:
            _type_: The list of old videos for the specified channel.
        """
        all_videos = []
        for youtube_channel in self._my_channels[id].youtube_channels:
            # Get uploads playlist
            res =  youtube.channels().list(
                part="contentDetails",
                id=youtube_channel
            ).execute()
            
            items = res.get("items")
            uploads_playlist_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
            next_page_token = None
            
            # Loop on videos
            while True:
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

                    # Check if older than 2018-01-01
                    if dt.year < 2019:
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
                                print(f"Video '{title}' has playername '{player}' in it")
                                has_player_1 = True
                                break
                    else:
                        has_player_1 = True
                    
                    # Check player names
                    if len(self._my_channels[id].players_2) >= 1:
                        for player in self._my_channels[id].players_2:
                            if player in title:
                                print(f"Video '{title}' has playername '{player}' in it")
                                has_player_2 = True
                                break
                    else:
                        has_player_2 = True
                    
                    # Check if video is valid
                    if has_player_1 is True and has_player_2 is True and has_character_1 is True and has_character_2 is True: 
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

                        


        
        
        
