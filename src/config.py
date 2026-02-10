from datetime import datetime

smash_characters=[
    "Mario",
    "Donkey Kong",
    "Link",
    "Samus",
    "Dark Samus",
    "Kirby",
    "Yoshi",
    "Fox",
    "Pikachu",
    "Luigi",
    "Ness",
    "Captain Falcon",
    "Jigglypuff",
    "Peach",
    "Daisy",
    "Bowser",
    "Ice Climbers",
    "Sheik",
    "Zelda",
    "Dr. Mario",
    "Pichu",
    "Falco",
    "Marth",
    "Lucina",
    "Young Link",
    "Ganondorf",
    "Mewtwo",
    "Roy",
    "Chrom",
    "Mr. Game & Watch",
    "Meta Knight",
    "Pit",
    "Dark Pit",
    "Zero Suit Samus",
    "Wario",
    "Snake",
    "Ike",
    "Pokemon Trainer",
    "Diddy Kong",
    "Lucas",
    "Sonic",
    "King Dedede",
    "Olimar",
    "Lucario",
    "R.O.B",
    "Toon Link",
    "Wolf",
    "Villager",
    "Mega Man",
    "Wii Fit Trainer",
    "Rosalina & Luma",
    "Little Mac",
    "Greninja",
    "Palutena",
    "Pac-man",
    "Robin",
    "Shulk",
    "Bowser Jr.",
    "Duck Hunt Duo",
    "Ryu",
    "Ken",
    "Cloud",
    "Corrin",
    "Bayonetta",
    "Inkling",
    "Ridley",
    "Simon",
    "Richter",
    "King K. Rool",
    "Isabelle",
    "Incineroar",
    "Piranha Plant",
    "Joker",
    "Hero",
    "Banjo & Kazooie",
    "Terry",
    "Byleth",
    "Min Min",
    "Steve",
    "Sephiroth",
    "Pyra & Mythra",
    "Kazuya",
    "Sora",
    "Mii Brawler",
    "Mii Swordfighter",
    "Mii Gunner"   
]

class _MyChannels:
    def __init__(self):
        self.characters = []
        self.players = []
        self.youtube_channels = []

        
class MyConfig:
    def __init__(self):
        self._my_channels = {}
        
    def _add_new_channel(self, id: int):
        self._my_channels[id] = _MyChannels()
    
    def add_character(self, id: int, char: str):
        if id not in self._my_channels.keys():
            self._add_new_channel(id)
        self._my_channels[id].characters.append(char)
        
    def add_youtube_channel(self, id: int, yt: str, youtube):
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
        
        self._my_channels[id].youtube_channels.append(items[0]["snippet"]["channelId"])
        return f"Channel '{yt}' was stored"

    def add_player(self, id: int, player: str):
        if id not in self._my_channels.keys():
            self._add_new_channel(id)
        if player in self._my_channels[id].players:
            return f"Player '{player}' was already stored"
        self._my_channels[id].players.append(player)
        return f"Player '{player}' was stored"
        
    def get_old_videos(self, id: int, youtube):
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
                    
                    has_character = False
                    has_player = False
                    
                    # Check character names
                    if len(self._my_channels[id].characters) >= 1:
                        for char in self._my_channels[id].characters:
                            if char in title:
                                print(f"Video '{title}' has character '{char}' in it")
                                has_character = True
                                break
                    else:
                        has_character = True
                        
                    # Check player names
                    if len(self._my_channels[id].players) >= 1:
                        for player in self._my_channels[id].players:
                            if player in title:
                                print(f"Video '{title}' has playername '{player}' in it")
                                has_player = True
                                break
                    else:
                        has_player = True
                    
                    # Check if video is valid
                    if has_player is True and has_character is True: 
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

                        


        
        
        
