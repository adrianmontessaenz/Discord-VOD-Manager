"""
bot.py

Main Discord bot entry point.
Author: MoloAdrian
Created: 2026-02-09
"""

# Import list.
import os
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
# From external libraries
import discord
from googleapiclient.discovery import build
from discord.ext import commands
import json
# From internal files
import config
import database

# Load environment variables from .env file
load_dotenv()
DISCORD_BOT_TOKEN=os.getenv("DISCORD_BOT_TOKEN")
YOUTUBE_API_KEY=os.getenv("YOUTUBE_API_KEY")

# Initialize YouTube API client
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

# Initialize Discord bot with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(
    command_prefix="!",
    intents=intents
)
bot.remove_command("help")

# Setup global variables to store config and tasks for each guild and channel.
m_config = {}
m_guild_tasks = {}
m_database = database.MyDatabase()

# ------------ Helper functions -------------
async def get_videos_for_channel(ctx, date: str = None, show_repeated: bool = False):
    """Gets videos for a channel and sends them to the channel. This is used in the get_old_videos command and in the automatic updates task.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
        date (str, optional): Date until which videos are retrieved. Defaults to None.
        show_repeated (bool, optional): Whether to show repeated videos. Defaults to False.

    Returns:
        _type_: None
    """
    video_list = await asyncio.to_thread(m_config[ctx.guild.id].get_old_videos, ctx.guild.id, ctx.channel.id, youtube, date, m_database)
    database_videos = m_database.get_videos(ctx.guild.id, ctx.channel.id)
    new_videos = [video for video in video_list if video['url'] not in database_videos]
    repeated_videos = [video for video in video_list if video['url'] in database_videos]
    for msg in new_videos:
        dt = datetime.fromisoformat(msg['publishedAt'].replace("Z", "+00:00"))
        formatted_date = dt.strftime("%Y-%m-%d %H:%M")
        await ctx.send(f"{msg['title']} ({formatted_date}): {msg['url']}")
        await asyncio.sleep(3)
        
    if repeated_videos and show_repeated:
        page_size = 8  # number of videos per page
        pages = [
            repeated_videos[i:i+page_size]
            for i in range(0, len(repeated_videos), page_size)
        ]

        current_page = 0

        embed = discord.Embed(
            title="📺 Already Sent Videos",
            description="\n".join([f"• {video['title']}" for video in pages[current_page]]),
            color=discord.Color.greyple()
        )
        embed.set_footer(text=f"Page {current_page + 1}/{len(pages)}")
        message = await ctx.send(embed=embed)

        if len(pages) == 1:
            return

        await message.add_reaction("⬅️")
        await message.add_reaction("➡️")

        def check(reaction, user):
            return (
                user == ctx.author
                and reaction.message.id == message.id
                and str(reaction.emoji) in ["⬅️", "➡️"]
            )

        while True:
            try:
                reaction, user = await bot.wait_for("reaction_add", timeout=120.0, check=check)

                if str(reaction.emoji) == "➡️":
                    current_page = (current_page + 1) % len(pages)
                elif str(reaction.emoji) == "⬅️":
                    current_page = (current_page - 1) % len(pages)

                embed.description = "\n".join([f"• {video['title']}" for video in pages[current_page]])
                embed.set_footer(text=f"Page {current_page + 1}/{len(pages)}")
                await message.edit(embed=embed)

                await message.remove_reaction(reaction, user)

            except asyncio.TimeoutError:
                await message.clear_reactions()
                break
                
# ------------- Events -------------
# Initialize bot and global info
@bot.event
async def on_ready():
    """Event that is called when the bot is ready. It loads the config for each guild and channel from the database 
    and stores it in memory, so it can be accessed faster when the commands are called.
    It also loads the list of characters from the config file.
    """
    file_json = {}
    if os.path.exists('data/config.json'):
        with open('data/config.json', 'r') as file:
            file_json = json.load(file)
    config.smash_characters = file_json["char_names"]

    for guild in bot.guilds:
        m_config[guild.id] = config.MyConfig()
        guild_data = m_database.load_guild_config(guild.id)
        print(f"Loaded config for guild {guild.name} ({guild.id}): {guild_data}")
        for channel_id, channel_data in guild_data.items():
            m_config[guild.id].add_channel(channel_id, channel_data["characters_1"], channel_data["characters_2"], channel_data["players_1"], channel_data["players_2"], channel_data["youtube_channels"], channel_data["enforce_characters"])
            

# Show welcome message and create memory for the server
@bot.event
async def on_guild_join(guild):
    """Event that is called when the bot joins a guild. It creates a welcome message and initializes the config for the guild in memory.

    Args:
        guild (_type_): The guild that the bot joined.
    """
    # Optional: send a welcome message
    if guild.text_channels[0].permissions_for(guild.me).send_messages:
        await guild.text_channels[0].send(
            "👋 Hi! Thanks for inviting me.\n"
            "Type `!help` to see what I can do."
        )
    
    m_config[guild.id] = config.MyConfig()
    
# Remove tasks from guild and remove memory stored for it.
@bot.event
async def on_guild_remove(guild):
    """Event that is called when the bot is removed from a guild. 
    It cancels any running tasks for the guild and removes the config and database for the guild from memory.

    Args:
        guild (_type_): The guild that the bot was removed from.
    """
    
    if guild.id in m_guild_tasks:
        for task in m_guild_tasks[guild.id].values():
            task.cancel()
        m_guild_tasks.pop(guild.id)
    m_config.pop(guild.id)
    m_database.clear_guild_database(guild.id)
    
# Remove tasks from guild and remove memory stored for it.
# This is in case the channel is deleted, so the bot doesn't keep history and tasks for channels that don't exist anymore.
@bot.event
async def on_guild_channel_delete(channel):
    """Event that is called when a channel is deleted. 
    It cancels any running tasks for the channel and removes the config and database for the channel from memory.  

    Args:
        channel (_type_): _description_
    """
    if channel.guild.id in m_guild_tasks and channel.id in m_guild_tasks[channel.guild.id]:
        for task in m_guild_tasks[channel.guild.id][channel.id].values():
            task.cancel()
        m_guild_tasks[channel.guild.id].pop(channel.id)
    m_config[channel.guild.id].remove_channel(channel.guild.id, channel.id, m_database)

# ------------- Commands -------------
# Simple command to test the bot is working and responding 
@bot.command()
async def hello(ctx):
    """Simple command to test the bot is working and responding. It mentions the user who sent the command."""
    await ctx.send(f"Hello {ctx.author.mention} 👋")

# Command to add character to the list of characters to search for in the videos.
@bot.command()
async def add_character_1(ctx, choice: str = None):
    """Command to add character to the list of characters to search for in the videos. 
    If two characters are added, the bot will search for videos that have both characters in the title.
    If only one character is added, it will search for videos that have that character in the title.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
        choice (str, optional): The character to be added. Defaults to None.
    """
    if not choice or choice not in config.smash_characters.keys():
        await ctx.send(f"Choose a valid character")
        return
    
    if ctx.guild.id in m_guild_tasks and ctx.channel.id in m_guild_tasks[ctx.guild.id] and "video_gathering_task" in m_guild_tasks[ctx.guild.id][ctx.channel.id]:
        await ctx.send(f"Cannot add character while video gathering is in progress. Please stop the video gathering task with !stop_video_gathering command, add the character and then start the video gathering again with !get_old_videos command.")
        return
    
    m_config[ctx.guild.id].add_character_1(ctx.guild.id, ctx.channel.id, choice, m_database)
    await ctx.send(f"Character stored for search!")

# Command to add character to the list of characters to search for in the videos.
# If two characters are added, the bot will search for videos that have both characters in the title.
# If only one character is added, it will search for videos that have that character in the title.
@bot.command()
async def add_character_2(ctx, choice: str = None):
    """Command to add character to the list of characters to search for in the videos. 
    If two characters are added, the bot will search for videos that have both characters in the title.
    If only one character is added, it will search for videos that have that character in the title.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
        choice (str, optional): The character to be added. Defaults to None.
    """
    if not choice or choice not in config.smash_characters:
        await ctx.send(f"Choose a valid character")
        return
    
    if ctx.guild.id in m_guild_tasks and ctx.channel.id in m_guild_tasks[ctx.guild.id] and "video_gathering_task" in m_guild_tasks[ctx.guild.id][ctx.channel.id]:
        await ctx.send(f"Cannot add character while video gathering is in progress. Please stop the video gathering task with !stop_video_gathering command, add the character and then start the video gathering again with !get_old_videos command.")
        return
    
    m_config[ctx.guild.id].add_character_2(ctx.guild.id, ctx.channel.id, choice, m_database)
    await ctx.send(f"Character stored for search!")
    
# Command to remove character from the list of characters to search for in the videos.
@bot.command()
async def remove_character_1(ctx, choice: str = None):
    """Command to remove character from the list of characters to search for in the videos.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
        choice (str, optional): The character to be removed. Defaults to None.
    """
    if not choice or choice not in config.smash_characters.keys():
        await ctx.send(f"Choose a valid character")
        return
    
    if ctx.guild.id in m_guild_tasks and ctx.channel.id in m_guild_tasks[ctx.guild.id] and "video_gathering_task" in m_guild_tasks[ctx.guild.id][ctx.channel.id]:
        await ctx.send(f"Cannot remove character while video gathering is in progress. Please stop the video gathering task with !stop_video_gathering command, remove the character and then start the video gathering again with !get_old_videos command.")
        return
    
    state = m_config[ctx.guild.id].remove_character_1(ctx.guild.id, ctx.channel.id, choice, m_database)
    await ctx.send(state)
    
# Command to remove character from the list of characters to search for in the videos.
@bot.command()
async def remove_character_2(ctx, choice: str = None):
    """Command to remove character from the list of characters to search for in the videos.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
        choice (str, optional): The character to be removed. Defaults to None.
    """
    if not choice or choice not in config.smash_characters.keys():
        await ctx.send(f"Choose a valid character")
        return
    
    if ctx.guild.id in m_guild_tasks and ctx.channel.id in m_guild_tasks[ctx.guild.id] and "video_gathering_task" in m_guild_tasks[ctx.guild.id][ctx.channel.id]:
        await ctx.send(f"Cannot remove character while video gathering is in progress. Please stop the video gathering task with !stop_video_gathering command, remove the character and then start the video gathering again with !get_old_videos command.")
        return
    
    state = m_config[ctx.guild.id].remove_character_2(ctx.guild.id, ctx.channel.id, choice, m_database)
    await ctx.send(state)
    
@bot.command()
async def list_characters(ctx):
    """Command to list characters added for player 1 and player 2.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
    """
    chars_1 = m_config[ctx.guild.id].get_characters_1(ctx.guild.id, ctx.channel.id, m_database)
    chars_2 = m_config[ctx.guild.id].get_characters_2(ctx.guild.id, ctx.channel.id, m_database)
    
    embed = discord.Embed(
        title=f"🎮 Characters to Search in {ctx.channel.name}",
        color=discord.Color.blurple()
    )
    
    embed.add_field(
        name="Player 1",
        value="\n".join(chars_1) if chars_1 else "No character added",
        inline=True
    )
    
    embed.add_field(
        name="Player 2",
        value="\n".join(chars_2) if chars_2 else "No character added",
        inline=True
    )
    
    await ctx.send(embed=embed)
    
# List of possible characters that can be added. This have to be in English, but the bot will search
# for the character in different languages, so you can add "Mario" and it will search for "Mario", "マリオ", "马里奥", etc.
@bot.command()
async def list_available_characters(ctx):
    """Command to list available characters that can be added to the search. 
    This command will show a paginated list of characters that can be added to the search, 
    so you can see all the possible characters.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
    """
    characters = list(config.smash_characters.keys())
    page_size = 15  # number of characters per page
    pages = [
        characters[i:i+page_size]
        for i in range(0, len(characters), page_size)
    ]

    current_page = 0

    embed = discord.Embed(
        title="🎮 Smash Characters",
        description="\n".join(pages[current_page]),
        color=discord.Color.blurple()
    )
    embed.set_footer(text=f"Page {current_page + 1}/{len(pages)}")
    message = await ctx.send(embed=embed)

    if len(pages) == 1:
        return  # no need for pagination

    # Add reactions for navigation
    await message.add_reaction("⬅️")
    await message.add_reaction("➡️")

    def check(reaction, user):
        return (
            user == ctx.author
            and reaction.message.id == message.id
            and str(reaction.emoji) in ["⬅️", "➡️"]
        )

    while True:
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=120.0, check=check)
            
            if str(reaction.emoji) == "➡️":
                current_page = (current_page + 1) % len(pages)
            elif str(reaction.emoji) == "⬅️":
                current_page = (current_page - 1) % len(pages)

            # Edit embed
            embed.description = "\n".join(pages[current_page])
            embed.set_footer(text=f"Page {current_page + 1}/{len(pages)}")
            await message.edit(embed=embed)
            
            # Remove the user's reaction
            await message.remove_reaction(reaction, user)

        except asyncio.TimeoutError:
            # Remove reactions after 2 minutes of inactivity
            await message.clear_reactions()
            break

# Command to add youtube channel to the list of channels to search for videos. 
# Some channels are already added by default.
# You can add a channel by its ID (starting with UC) or by its @name. If you add it by @name, 
# the bot will search for the channel and add it if it finds it.
@bot.command()
async def add_youtube_channel(ctx, channel: str = None):
    """Command to add youtube channel to the list of channels to search for videos.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
        channel (str, optional): The youtube channel to be added. Defaults to None.
    """
    if not channel:
        await ctx.send(f"Provide a youtube channel (Either the ID starting with UC or the @)")
        return
    
    if ctx.guild.id in m_guild_tasks and ctx.channel.id in m_guild_tasks[ctx.guild.id] and "video_gathering_task" in m_guild_tasks[ctx.guild.id][ctx.channel.id]:
        await ctx.send(f"Cannot add youtube channel while video gathering is in progress. Please stop the video gathering task with !stop_video_gathering command, add the channel and then start the video gathering again with !get_old_videos command.")
        return
    
    state = m_config[ctx.guild.id].add_youtube_channel(ctx.guild.id, ctx.channel.id, channel, youtube, m_database)
    await ctx.send(state)
    
@bot.command()
async def remove_youtube_channel(ctx, channel: str = None):
    """Command to remove youtube channel from the list of channels to search for videos.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
        channel (str, optional): The youtube channel to be removed. Defaults to None.
    """
    if not channel:
        await ctx.send(f"Provide a youtube channel name (See your list with !list_youtube_channels)")
        return
    
    if ctx.guild.id in m_guild_tasks and ctx.channel.id in m_guild_tasks[ctx.guild.id] and "video_gathering_task" in m_guild_tasks[ctx.guild.id][ctx.channel.id]:
        await ctx.send(f"Cannot remove youtube channel while video gathering is in progress. Please stop the video gathering task with !stop_video_gathering command, remove the channel and then start the video gathering again with !get_old_videos command.")
        return
    
    state = m_config[ctx.guild.id].remove_youtube_channel(ctx.guild.id, ctx.channel.id, channel, m_database)
    await ctx.send(state)    

# Command to list youtube channels added. If there are more than 15 channels, it will paginate the list.
@bot.command()
async def list_youtube_channels(ctx):
    """Command to list youtube channels added. If there are more than 15 channels, it will paginate the list.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
    """
    channels = m_config[ctx.guild.id].get_youtube_channels(ctx.guild.id, ctx.channel.id)
    if not channels:
        await ctx.send(f"No youtube channels stored yet.")
        return
    
    page_size = 15  # number of characters per page
    pages = [
        channels[i:i+page_size]
        for i in range(0, len(channels), page_size)
    ]

    current_page = 0

    embed = discord.Embed(
        title="🎮 Youtube Channels",
        description="\n".join(pages[current_page]),
        color=discord.Color.blurple()
    )
    embed.set_footer(text=f"Page {current_page + 1}/{len(pages)}")
    message = await ctx.send(embed=embed)

    if len(pages) == 1:
        return  # no need for pagination

    # Add reactions for navigation
    await message.add_reaction("⬅️")
    await message.add_reaction("➡️")

    def check(reaction, user):
        return (
            user == ctx.author
            and reaction.message.id == message.id
            and str(reaction.emoji) in ["⬅️", "➡️"]
        )

    while True:
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=120.0, check=check)
            
            if str(reaction.emoji) == "➡️":
                current_page = (current_page + 1) % len(pages)
            elif str(reaction.emoji) == "⬅️":
                current_page = (current_page - 1) % len(pages)

            # Edit embed
            embed.description = "\n".join(pages[current_page])
            embed.set_footer(text=f"Page {current_page + 1}/{len(pages)}")
            await message.edit(embed=embed)
            
            # Remove the user's reaction
            await message.remove_reaction(reaction, user)

        except asyncio.TimeoutError:
            # Remove reactions after 2 minutes of inactivity
            await message.clear_reactions()
            break
    
# Command to add player to the list of players to search for in the videos.
@bot.command()
async def add_player_1(ctx, player: str = None):
    """Command to add player to the list of players to search for in the videos.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
        player (str, optional): The player to be added. Defaults to None.
    """
    if not player:
        await ctx.send(f"No player set.")
        return
    
    if ctx.guild.id in m_guild_tasks and ctx.channel.id in m_guild_tasks[ctx.guild.id] and "video_gathering_task" in m_guild_tasks[ctx.guild.id][ctx.channel.id]:
        await ctx.send(f"Cannot add player while video gathering is in progress. Please stop the video gathering task with !stop_video_gathering command, add the player and then start the video gathering again with !get_old_videos command.")
        return
    
    state = m_config[ctx.guild.id].add_player_1(ctx.guild.id, ctx.channel.id, player, m_database)
    await ctx.send(state)

# Command to add player to the list of players to search for in the videos.
# If two players are added, the bot will search for videos that have both players in the title. 
# If only one player is added, it will search for videos that have that player in the title.
@bot.command()
async def add_player_2(ctx, player: str = None):
    """Command to add player to the list of players to search for in the videos.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
        player (str, optional): The player to be added. Defaults to None.
    """
    if not player:
        await ctx.send(f"No player set.")
        return
    
    if ctx.guild.id in m_guild_tasks and ctx.channel.id in m_guild_tasks[ctx.guild.id] and "video_gathering_task" in m_guild_tasks[ctx.guild.id][ctx.channel.id]:
        await ctx.send(f"Cannot add player while video gathering is in progress. Please stop the video gathering task with !stop_video_gathering command, add the player and then start the video gathering again with !get_old_videos command.")
        return
    
    state = m_config[ctx.guild.id].add_player_2(ctx.guild.id, ctx.channel.id, player, m_database)
    await ctx.send(state)

# Command to remove player from the list of players to search for in the videos.
@bot.command()
async def remove_player_1(ctx, player: str = None):
    """Command to remove player from the list of players to search for in the videos.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
        player (str, optional): The player to be removed. Defaults to None.
    """
    if not player:
        await ctx.send(f"No player set.")
        return

    if ctx.guild.id in m_guild_tasks and ctx.channel.id in m_guild_tasks[ctx.guild.id] and "video_gathering_task" in m_guild_tasks[ctx.guild.id][ctx.channel.id]:
        await ctx.send(f"Cannot remove player while video gathering is in progress. Please stop the video gathering task with !stop_video_gathering command, remove the player and then start the video gathering again with !get_old_videos command.")
        return 
        
    state = m_config[ctx.guild.id].remove_player_1(ctx.guild.id, ctx.channel.id, player, m_database)
    await ctx.send(state)

# Command to remove player from the list of players to search for in the videos.  
@bot.command()
async def remove_player_2(ctx, player: str = None):
    """Command to remove player from the list of players to search for in the videos.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
        player (str, optional): The player to be removed. Defaults to None.
    """
    if not player:
        await ctx.send(f"No player set.")
        return

    if ctx.guild.id in m_guild_tasks and ctx.channel.id in m_guild_tasks[ctx.guild.id] and "video_gathering_task" in m_guild_tasks[ctx.guild.id][ctx.channel.id]:
        await ctx.send(f"Cannot remove player while video gathering is in progress. Please stop the video gathering task with !stop_video_gathering command, remove the player and then start the video gathering again with !get_old_videos command.")
        return
    
    state = m_config[ctx.guild.id].remove_player_2(ctx.guild.id, ctx.channel.id, player, m_database)
    await ctx.send(state)

# Command to list players added for player 1 and player 2.
@bot.command()
async def list_players(ctx):
    """Command to list players added for player 1 and player 2.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
    """
    players_1 = m_config[ctx.guild.id].get_players_1(ctx.guild.id, ctx.channel.id, m_database)
    players_2 = m_config[ctx.guild.id].get_players_2(ctx.guild.id, ctx.channel.id, m_database)
    
    embed = discord.Embed(
        title=f"🎮 Players to Search in {ctx.channel.name}",
        color=discord.Color.blurple()
    )
    
    embed.add_field(
        name="Player 1",
        value="\n".join(players_1) if players_1 else "No player added",
        inline=True
    )
    
    embed.add_field(
        name="Player 2",
        value="\n".join(players_2) if players_2 else "No player added",
        inline=True
    )
    
    await ctx.send(embed=embed)

# Command to get old videos from configured YouTube channels. 
# This will search for videos that match the characters and players added in the configuration,
# (but it will not check if the video was already sent or not, so it may send some videos that were already sent before) (To be changed). 
# It will send the videos in the order they were published, starting from the oldest one. 
# Depending on the amount of videos and channels configured, this command may take a while to complete, so be patient after running it.
@bot.command()
async def get_old_videos(ctx, date: str = None):
    """Command to get old videos from configured YouTube channels.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
        date (str, optional): The date until to which search for videos. Defaults to None.
    """
    await ctx.send(f"This will take a while depending on channel history and video ammount")
    m_guild_tasks[ctx.guild.id][ctx.channel.id]["video_gathering_task"] = asyncio.create_task(get_videos_for_channel(ctx, date, True))
        
# Command to enforce that characters are also in the title of the videos. Some VODs don't show the name on titles, 
# so by default this is set to False, but you can set it to True if you want to enforce that the character is 
# also in the title of the videos. 
# This will make the search more strict, but it will also make sure that the videos that are sent are more relevant 
# to the characters you added.
@bot.command()
async def enforce_characters(ctx, state : bool):
    """Command to set the enforce characters setting. This setting will enforce that the characters added are also
    in the title of the videos. Some VODs don't show the name on titles, so by default this is set to False,
    but you can set it to True if you want to enforce that the character is

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
        state (bool): The state to set the enforce characters setting to.
    """
    if ctx.guild.id in m_guild_tasks and ctx.channel.id in m_guild_tasks[ctx.guild.id] and "video_gathering_task" in m_guild_tasks[ctx.guild.id][ctx.channel.id]:
        await ctx.send(f"Cannot change enforce characters setting while video gathering is in progress. Please stop the video gathering task with !stop_video_gathering command, change the setting and then start the video gathering again with !get_old_videos command.")
        return
    
    m_config[ctx.guild.id].enforce_characters(ctx.guild.id, ctx.channel.id, state, m_database)
    await ctx.send(f"Enforce characters set to '{state}'")
    
@bot.command()
async def update_frequently(ctx):
    """Command to enable automatic updates for a channel. This will make the bot search for new videos every 15 minutes 
    and send them to the channel.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
    """
    if ctx.channel.id in m_guild_tasks[ctx.guild.id]:
        await ctx.send("Automatic updates are already enabled for this channel.")
        return

    async def update_task():
        while True:
            if ctx.guild.id in m_guild_tasks and ctx.channel.id in m_guild_tasks[ctx.guild.id] and "video_gathering_task" in m_guild_tasks[ctx.guild.id][ctx.channel.id]:
                await ctx.send(f"Skipping update because video gathering is in progress. Please wait for it to finish to get the latest videos, or stop the video gathering task with !stop_video_gathering command to allow updates to run.")
                await asyncio.sleep(900)  # wait for 15 minutes before checking again
                continue
            date = (datetime.now() - timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%SZ")
            await get_videos_for_channel(ctx, date)
            await asyncio.sleep(900)  # wait for 15 minutes

    task = asyncio.create_task(update_task())
    m_guild_tasks[ctx.guild.id][ctx.channel.id]["update_task"] = task
    await ctx.send("Automatic updates enabled for this channel every 15 minutes.")
    
@bot.command()
async def stop_updates(ctx):
    """Stops automatic updates for a channel.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
    """
    if ctx.guild.id not in m_guild_tasks or ctx.channel.id not in m_guild_tasks[ctx.guild.id]:
        await ctx.send("Automatic updates are not enabled for this channel.")
        return
    task = m_guild_tasks[ctx.guild.id][ctx.channel.id].pop("update_task", None)
    if task:
        task.cancel()
        await ctx.send("Automatic updates stopped for this channel.")
    else:
        await ctx.send("Automatic updates are not enabled for this channel.")

@bot.command()
async def stop_video_gathering(ctx):
    """Stops video gathering for a channel.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
    """
    if ctx.guild.id not in m_guild_tasks or ctx.channel.id not in m_guild_tasks[ctx.guild.id]:
        await ctx.send("Video gathering is not enabled for this channel.")
        return
    task = m_guild_tasks[ctx.guild.id][ctx.channel.id].pop("video_gathering_task", None)
    if task:
        task.cancel()
        await ctx.send("Video gathering stopped for this channel.")
    else:
        await ctx.send("Video gathering is not enabled for this channel.")
    
# Command to show all available commands and how to use them.
@bot.command()
async def help(ctx):
    """Command to show all available commands and how to use them. 
    It will show a list of all commands with a brief description of what they do.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
    """
    embed = discord.Embed(
        title="🤖 Bot Commands",
        description="Here’s a list of available commands",
        color=discord.Color.blurple()
    )
    
    embed.add_field(
        name="📺 !add_character_1 [charactername] / !add_character_2[charactername] ",
        value="Adds character to search for player 1 / player 2. You have to add the character in English, but in the search it will use its name in different languages",
        inline=False
    )
    
    embed.add_field(
        name="📺 !remove_character_1 [charactername] / !remove_character_2 [charactername]",
        value="Removes character to search for player 1 / player 2. You have to add the character in English, but in the search it will use its name in different languages",
        inline=False
    )
    
    embed.add_field(
        name="📺 !list_characters",
        value="Lists the characters you added for player 1 and player 2 in this channel",
        inline=False
    )
    
    embed.add_field(
        name="📺 !list_available_characters",
        value="Lists all available characters that can be added to search for player 1 and player 2",
        inline=False
    )

    embed.add_field(
        name="📺 !add_player_1 [playername] / !add_player_2 [playername]",
        value="Adds player to search for player 1 / player 2",
        inline=False
    )
    
    embed.add_field(
        name="📺 !remove_player_1 [playername] / !remove_player_2 [playername]",
        value="Removes player to search for player 1 / player 2",
        inline=False
    )
    
    embed.add_field(
        name="📺 !list_players",
        value="Lists the players you added for player 1 and player 2 in this channel",
        inline=False
    )

    embed.add_field(
        name="📺 !add_youtube_channel [ID]",
        value="Adds youtube channel to the list of channels to get vods from. A default list is already provided with big channels",
        inline=False
    )
    
    embed.add_field(
        name="📺 !remove_youtube_channel [Name]",
        value="Removes youtube channel from the list of channels to get vods from. Use !list_youtube_channels to see the list of channels you added",
        inline=False
    )
    
    embed.add_field(
        name="📺 !list_youtube_channels",
        value="Lists the youtube channels you added to get vods from",
        inline=False
    )
    
    embed.add_field(
        name="📺 !enforce_characters [True / False]",
        value="Change if you want to enforce that the character is also in the title of the videos or not. Some VODs don't show the name on titles",
        inline=False
    )

    embed.add_field(
        name="📺 !get_old_videos",
        value="Fetches old videos from configured YouTube channels.",
        inline=False
    )

    embed.add_field(
        name="🔁 !update_frequently",
        value="Starts automatic YouTube updates every 15 minutes for this channel.",
        inline=False
    )

    embed.add_field(
        name="⛔ !stop_updates",
        value="Stops automatic updates for this channel.",
        inline=False
    )
    
    embed.add_field(
        name="⛔ !stop_video_gathering",
        value="Stops the video gathering process started by !get_old_videos command.",
        inline=False
    )

    embed.add_field(
        name="ℹ️ !help",
        value="Shows this help message.",
        inline=False
    )

    embed.set_footer(text="Bot made to gather VODs easily and store them on Discord")

    await ctx.send(embed=embed)
    
# Run bot
bot.run(DISCORD_BOT_TOKEN)