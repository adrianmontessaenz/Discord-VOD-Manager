"""
bot.py

Main Discord bot entry point.
Author: MoloAdrian
Created: 2026-02-09
"""

# Import list.
import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv
# From external libraries
import discord
from discord.ext import commands, tasks
# From internal files
import config
from repositories import (SqliteGuildSettingsRepository, SqliteSyncStateRepository, SqliteVodRepository,
                          YggdrasilClient, YggdrasilError, YggdrasilUnavailable, build_vod_repository)
from filters import vod_matches
from vod_sync import publish_new_vods, format_vod, urls_in_message

# Load environment variables from .env file
load_dotenv()
DISCORD_BOT_TOKEN=os.getenv("DISCORD_BOT_TOKEN")
YGGDRASIL_URL=os.getenv("YGGDRASIL_URL")
YGGDRASIL_TOKEN=os.getenv("YGGDRASIL_TOKEN")

# Yggdrasil client (channel sources and history). None when Yggdrasil is not configured.
m_yggdrasil = YggdrasilClient(YGGDRASIL_URL, YGGDRASIL_TOKEN) if YGGDRASIL_URL and YGGDRASIL_TOKEN else None

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
m_database = SqliteGuildSettingsRepository()  # server settings + publication history (stays in Ratatoskr)
m_vods = SqliteVodRepository()  # local VOD cache (fallback when Yggdrasil is down)
m_source = build_vod_repository()  # where VODs are read from: Yggdrasil, or the local cache if not configured
m_sync_state = SqliteSyncStateRepository()  # revision cursor of the automatic sync

SYNC_MINUTES = 15


# ------------ Helper functions -------------
def other_users_of(channel_id: str) -> bool:
    """True if any local text channel (any guild) still uses this YouTube channel."""
    for cfg in m_config.values():
        if cfg.uses_youtube_channel(channel_id):
            return True
    return False


async def send_to_channel(guild_id: int, channel_id: int, text: str) -> bool:
    """Send function used by the automatic sync. False if the Discord channel is unreachable."""
    channel = bot.get_channel(channel_id)
    if channel is None:
        return False
    try:
        await channel.send(text)
    except discord.Forbidden:
        return False
    return True


@tasks.loop(minutes=SYNC_MINUTES)
async def vod_sync_loop():
    """One tick of the automatic VOD publication for every channel with auto_update enabled."""
    targets = []
    for guild_id, channel_id in m_database.list_auto_update_channels():
        if guild_id not in m_config:
            continue
        targets.extend(m_config[guild_id].targets(guild_id, [channel_id], m_database))
    try:
        await publish_new_vods(source=m_source, state=m_sync_state, settings=m_database, cache=m_vods,
                               targets=targets, send=send_to_channel, char_aliases=config.char_aliases())
    except YggdrasilError as error:
        print(f"VOD sync skipped, Yggdrasil unavailable: {error}")
    except Exception as error:
        print(f"VOD sync failed: {error!r}")


def collect_vods(ctx, date: str = None):
    """VODs of this text channel that pass its filter. Returns (vods, notice) or raises ValueError on a bad date."""
    if date is not None:
        datetime.strptime(date, "%Y-%m-%d")  # ValueError on bad format
    notice = None
    try:
        vods = m_source.list()
    except YggdrasilUnavailable:
        vods = m_vods.list()
        notice = "⚠️ Yggdrasil is not reachable, showing the last VODs cached locally."
    cfg = m_config[ctx.guild.id]
    ids = set(cfg.targets(ctx.guild.id, [ctx.channel.id], m_database)[0].youtube_channel_ids)
    flt = cfg.get_filter(ctx.guild.id, ctx.channel.id, m_database)
    aliases = config.char_aliases()
    selected = [v for v in vods if v.youtube_channel_id in ids and vod_matches(v, flt, aliases)
                and (date is None or v.published_at[:10] >= date)]
    return sorted(selected, key=lambda v: v.published_at), notice


# ------------ Helper functions (display) -------------
async def get_videos_for_channel(ctx, date: str = None, show_repeated: bool = False):
    """Gets videos for a channel and sends them to the channel. This is used in the get_old_videos command and in the automatic updates task.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
        date (str, optional): Date until which videos are retrieved. Defaults to None.
        show_repeated (bool, optional): Whether to show repeated videos. Defaults to False.

    Returns:
        _type_: None
    """
    try:
        vods, notice = await asyncio.to_thread(collect_vods, ctx, date)
    except ValueError:
        await ctx.send("Incorrect date format. Use YYYY-MM-DD.")
        return
    if notice:
        await ctx.send(notice)
    published = m_database.get_published(ctx.guild.id, ctx.channel.id)
    new_videos = [{"title": v.title, "url": v.url, "vod": v} for v in vods if v.video_id not in published]
    repeated_videos = [{"title": v.title, "url": v.url} for v in vods if v.video_id in published]
    for item in new_videos:
        vod = item["vod"]
        # Claim before sending so two concurrent runs never post the same VOD twice.
        if not m_database.add_published(ctx.guild.id, ctx.channel.id, vod.video_id, vod.title, vod.url, vod.published_at):
            continue
        try:
            await ctx.send(format_vod(vod))
        except BaseException:
            m_database.remove_published(ctx.guild.id, ctx.channel.id, vod.video_id)
            raise
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
    config.smash_characters = config._read_config_file().get("char_names", {})

    for guild in bot.guilds:
        m_config[guild.id] = config.MyConfig()
        guild_data = m_database.load_guild_config(guild.id)
        print(f"Loaded config for guild {guild.name} ({guild.id}): {guild_data}")
        if not guild_data:
            print(f"No config found for guild {guild.name} ({guild.id}), initializing empty config.")
            continue
        for channel_id, channel_data in guild_data.items():
            enforce_values = {
                "enforce_character_1": channel_data["enforce_character_1"] if "enforce_character_1" in channel_data else False,
                "enforce_character_2": channel_data["enforce_character_2"] if "enforce_character_2" in channel_data else False,
                "enforce_player_1": channel_data["enforce_player_1"] if "enforce_player_1" in channel_data else True,
                "enforce_player_2": channel_data["enforce_player_2"] if "enforce_player_2" in channel_data else True
            }
            m_config[guild.id].add_channel(channel_id, channel_data["characters_1"], channel_data["characters_2"], channel_data["players_1"], channel_data["players_2"], channel_data["youtube_channels"], enforce_values)

    await asyncio.to_thread(register_local_channels_in_yggdrasil)
    if not vod_sync_loop.is_running():
        vod_sync_loop.start()


def register_local_channels_in_yggdrasil():
    """Best effort: make sure every YouTube channel stored locally is also watched by Yggdrasil."""
    if m_yggdrasil is None:
        print("Yggdrasil is not configured (YGGDRASIL_URL / YGGDRASIL_TOKEN): no VODs will be published.")
        return
    try:
        known = {s["channel_id"] for s in m_yggdrasil.list_sources()}
        for cfg in m_config.values():
            for name, channel_id in cfg.all_youtube_channels().items():
                if channel_id not in known:
                    m_yggdrasil.add_source(channel_id, name=name)
                    known.add(channel_id)
    except YggdrasilError as error:
        print(f"Could not register local YouTube channels in Yggdrasil: {error}")


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

# Handle errors in commands and send a message to the channel with the error. If the error is CommandNotFound, it sends a message saying that the command was not found and to use !help to see the list of available commands.
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"❌ Command '{ctx.message.content}' not found. Type `!help` to see the list of available commands.")
    else:
        await ctx.send(f"An error occurred while processing the command: {str(error)}")
        
@bot.event
async def on_message_delete(message):
    """Event that is called when a message is deleted. It checks if the message was sent by the bot and if it contains a video link, it removes the video from the database to avoid showing it again in the future.

    Args:
        message (_type_): The message that was deleted.
    """
    if message.guild is None or message.author != bot.user:
        return
    for url in urls_in_message(message.content):
        m_database.remove_published_by_url(message.guild.id, message.channel.id, url)

# ------------- Commands -------------
# Simple command to test the bot is working and responding 
@bot.command()
async def hello(ctx):
    """Simple command to test the bot is working and responding. It mentions the user who sent the command."""
    await ctx.send(f"Hello {ctx.author.mention} 👋")

# Command to add character to the list of characters to search for in the videos.
@bot.command()
async def add_character_1(ctx, *choices: str):
    """Command to add character to the list of characters to search for in the videos. 
    If two characters are added, the bot will search for videos that have both characters in the title.
    If only one character is added, it will search for videos that have that character in the title.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
        choice (str, optional): The character to be added. Defaults to None.
    """
    if not choices:
        await ctx.send(f"No character(s) provided. Please provide a character to add.")
        return
    
    if ctx.guild.id in m_guild_tasks and ctx.channel.id in m_guild_tasks[ctx.guild.id] and "video_gathering_task" in m_guild_tasks[ctx.guild.id][ctx.channel.id]:
        await ctx.send(f"Cannot add character while video gathering is in progress. Please stop the video gathering task with !stop_video_gathering command, add the character and then start the video gathering again with !get_old_videos command.")
        return
    
    valid_choices = [choice for choice in choices if choice in config.smash_characters]
    added_characters = []
    repeated_characters = []
    for choice in valid_choices:
        state =m_config[ctx.guild.id].add_character_1(ctx.guild.id, ctx.channel.id, choice, m_database)
        if "already" in state.lower():
            repeated_characters.append(choice)
        else:
            added_characters.append(choice)
    
    # Merge the messages for added characters and repeated characters into one message to avoid spamming the channel with multiple messages if multiple characters are added at once.    
    final_message = ""
    if added_characters:
        final_message += f"Character(s) '{', '.join(added_characters)}' added to search!\n"
    if repeated_characters:
        final_message += f"Character(s) '{', '.join(repeated_characters)}' were already in the list.\n"
    if len(valid_choices) < len(choices):
        invalid_choices = [choice for choice in choices if choice not in config.smash_characters]
        final_message += f"These characters are not valid and were not added: {', '.join(invalid_choices)}. Use !list_available_characters to see the list of valid characters."
        
    await ctx.send(final_message)
    
# Command to add character to the list of characters to search for in the videos.
# If two characters are added, the bot will search for videos that have both characters in the title.
# If only one character is added, it will search for videos that have that character in the title.
@bot.command()
async def add_character_2(ctx, *choices: str):
    """Command to add character to the list of characters to search for in the videos. 
    If two characters are added, the bot will search for videos that have both characters in the title.
    If only one character is added, it will search for videos that have that character in the title.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
        choice (str, optional): The character to be added. Defaults to None.
    """
    if not choices:
        await ctx.send(f"No character(s) provided. Please provide a character to add.")
        return
    
    if ctx.guild.id in m_guild_tasks and ctx.channel.id in m_guild_tasks[ctx.guild.id] and "video_gathering_task" in m_guild_tasks[ctx.guild.id][ctx.channel.id]:
        await ctx.send(f"Cannot add character while video gathering is in progress. Please stop the video gathering task with !stop_video_gathering command, add the character and then start the video gathering again with !get_old_videos command.")
        return
    
    valid_choices = [choice for choice in choices if choice in config.smash_characters]
    added_characters = []
    repeated_characters = []
    for choice in valid_choices:
        state = m_config[ctx.guild.id].add_character_2(ctx.guild.id, ctx.channel.id, choice, m_database)
        if "already" in state.lower():
            repeated_characters.append(choice)
        else:
            added_characters.append(choice)
    
    # Merge the messages for added characters and repeated characters into one message to avoid spamming the channel with multiple messages if multiple characters are added at once.    
    final_message = ""
    if added_characters:
        final_message += f"Character(s) '{', '.join(added_characters)}' added to search!\n"
    if repeated_characters:
        final_message += f"Character(s) '{', '.join(repeated_characters)}' were already in the list.\n"
    if len(valid_choices) < len(choices):
        invalid_choices = [choice for choice in choices if choice not in config.smash_characters]
        final_message += f"These characters are not valid and were not added: {', '.join(invalid_choices)}. Use !list_available_characters to see the list of valid characters."
    await ctx.send(final_message)
    
# Command to remove character from the list of characters to search for in the videos.
@bot.command()
async def remove_character_1(ctx, *choices: str):
    """Command to remove character from the list of characters to search for in the videos.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
        choice (str, optional): The character to be removed. Defaults to None.
    """
    if not choices:
        await ctx.send(f"No character(s) provided. Please provide a character to remove.")
        return
    
    if ctx.guild.id in m_guild_tasks and ctx.channel.id in m_guild_tasks[ctx.guild.id] and "video_gathering_task" in m_guild_tasks[ctx.guild.id][ctx.channel.id]:
        await ctx.send(f"Cannot remove character while video gathering is in progress. Please stop the video gathering task with !stop_video_gathering command, remove the character and then start the video gathering again with !get_old_videos command.")
        return
    
    valid_choices = [choice for choice in choices if choice in config.smash_characters]
    removed_characters = []
    missing_characters = []
    for choice in valid_choices:
        state = m_config[ctx.guild.id].remove_character_1(ctx.guild.id, ctx.channel.id, choice, m_database)
        if "removed" in state.lower():
            removed_characters.append(choice)
        elif "not found" in state.lower():
            missing_characters.append(choice)
            
    final_message = ""
    if removed_characters:
        final_message += f"Character(s) '{', '.join(removed_characters)}' removed from search!\n"
    if missing_characters:
        final_message += f"Character(s) '{', '.join(missing_characters)}' were not in the list.\n"        
    if len(valid_choices) < len(choices):
        invalid_choices = [choice for choice in choices if choice not in config.smash_characters]
        final_message += f"These characters are not valid and were not removed: {', '.join(invalid_choices)}. Use !list_available_characters to see the list of valid characters."
    await ctx.send(final_message)
    
# Command to remove character from the list of characters to search for in the videos.
@bot.command()
async def remove_character_2(ctx, *choices: str):
    """Command to remove character from the list of characters to search for in the videos.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
        choice (str, optional): The character to be removed. Defaults to None.
    """
    if not choices:
        await ctx.send(f"No character(s) provided. Please provide a character to remove.")
        return
    
    if ctx.guild.id in m_guild_tasks and ctx.channel.id in m_guild_tasks[ctx.guild.id] and "video_gathering_task" in m_guild_tasks[ctx.guild.id][ctx.channel.id]:
        await ctx.send(f"Cannot remove character while video gathering is in progress. Please stop the video gathering task with !stop_video_gathering command, remove the character and then start the video gathering again with !get_old_videos command.")
        return
    
    valid_choices = [choice for choice in choices if choice in config.smash_characters]
    removed_characters = []
    missing_characters = []
    for choice in valid_choices:
        state = m_config[ctx.guild.id].remove_character_2(ctx.guild.id, ctx.channel.id, choice, m_database)
        if "removed" in state.lower():
            removed_characters.append(choice)
        elif "not found" in state.lower():
            missing_characters.append(choice)
    
    final_message = ""
    if removed_characters:
        final_message += f"Character(s) '{', '.join(removed_characters)}' removed from search!\n"
    if missing_characters:
        final_message += f"Character(s) '{', '.join(missing_characters)}' were not in the list.\n"        
    if len(valid_choices) < len(choices):
        invalid_choices = [choice for choice in choices if choice not in config.smash_characters]
        final_message += f"These characters are not valid and were not removed: {', '.join(invalid_choices)}. Use !list_available_characters to see the list of valid characters."
    await ctx.send(final_message)
    
@bot.command()
async def enforce_character_1(ctx, state: str):
    """Command to enforce that character 1 is in the title of the video. 

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
        state (str): on/off to enable or disable enforcing player 1 in the title of the video.
    """
    if state.lower() not in ["on", "off"]:
        await ctx.send(f"Invalid state '{state}'. Please provide 'on' or 'off'.")
        return
    
    m_config[ctx.guild.id].enforce_character_1(ctx.guild.id, ctx.channel.id, state.lower() == "on", m_database)
    await ctx.send(f"Enforcing character 1 in video titles {'enabled' if state.lower() == 'on' else 'disabled'}.")

@bot.command()
async def enforce_character_2(ctx, state: str):
    """Command to enforce that character 2 is in the title of the video.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
        state (str): on/off to enable or disable enforcing player 2 in the title of the video.
    """
    if state.lower() not in ["on", "off"]:
        await ctx.send(f"Invalid state '{state}'. Please provide 'on' or 'off'.")
        return
    
    m_config[ctx.guild.id].enforce_character_2(ctx.guild.id, ctx.channel.id, state.lower() == "on", m_database)
    await ctx.send(f"Enforcing character 2 in video titles {'enabled' if state.lower() == 'on' else 'disabled'}.")

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
async def add_youtube_channel(ctx, *channels: str):
    """Command to add youtube channel to the list of channels to search for videos.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
        channel (str, optional): The youtube channel to be added. Defaults to None.
    """
    if not channels:
        await ctx.send(f"Provide youtube channel(s) (Either the ID starting with UC or the @)")
        return
    
    if ctx.guild.id in m_guild_tasks and ctx.channel.id in m_guild_tasks[ctx.guild.id] and "video_gathering_task" in m_guild_tasks[ctx.guild.id][ctx.channel.id]:
        await ctx.send(f"Cannot add youtube channel while video gathering is in progress. Please stop the video gathering task with !stop_video_gathering command, add the channel and then start the video gathering again with !get_old_videos command.")
        return
    
    added_channels = []
    repeated_channels = []
    incorrect_channels = []
    failed_messages = []
    for channel in channels:
        state = await asyncio.to_thread(m_config[ctx.guild.id].add_youtube_channel, ctx.guild.id, ctx.channel.id, channel, m_yggdrasil, m_database)
        if "could not register" in state.lower():
            failed_messages.append(state)
        elif "stored" in state.lower() and "already" not in state.lower():
            added_channels.append(channel)
        elif "already" in state.lower():
            repeated_channels.append(channel)
        elif "not found" in state.lower() or "invalid" in state.lower():
            incorrect_channels.append(channel)

    # Merge the messages for added channels and repeated channels into one message to avoid spamming the channel with multiple messages if multiple channels are added at once.
    final_message = ""
    if added_channels:
        final_message += f"Youtube channel(s) '{', '.join(added_channels)}' stored for search!\n"
    if repeated_channels:
        final_message += f"Youtube channel(s) '{', '.join(repeated_channels)}' were already in the list.\n"
    if incorrect_channels:
        final_message += f"These channels were not found or have an invalid format and were not added: {', '.join(incorrect_channels)}. Please provide a channel ID starting with 'UC' or a channel name starting with '@'.\n"
    for failure in sorted(set(failed_messages)):
        final_message += f"{failure}\n"
    await ctx.send(final_message)
    
@bot.command()
async def remove_youtube_channel(ctx, *channels: str):
    """Command to remove youtube channel from the list of channels to search for videos.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
        channel (str, optional): The youtube channel to be removed. Defaults to None.
    """
    if not channels:
        await ctx.send(f"Provide youtube channel(s) to remove (See your list with !list_youtube_channels)")
        return
    
    if ctx.guild.id in m_guild_tasks and ctx.channel.id in m_guild_tasks[ctx.guild.id] and "video_gathering_task" in m_guild_tasks[ctx.guild.id][ctx.channel.id]:
        await ctx.send(f"Cannot remove youtube channel while video gathering is in progress. Please stop the video gathering task with !stop_video_gathering command, remove the channel and then start the video gathering again with !get_old_videos command.")
        return
    
    removed_channels = []
    missing_channels = []
    for channel in channels:
        state = await asyncio.to_thread(m_config[ctx.guild.id].remove_youtube_channel, ctx.guild.id, ctx.channel.id, channel,
                                        m_database, m_yggdrasil, other_users_of)
        if "removed" in state.lower():
            removed_channels.append(channel)
        elif "not found" in state.lower():
            missing_channels.append(channel)
    
    final_message = ""
    if removed_channels:
        final_message += f"Youtube channel(s) '{', '.join(removed_channels)}' removed from search!\n"
    if missing_channels:
        final_message += f"Youtube channel(s) '{', '.join(missing_channels)}' were not in the list.\n"
    await ctx.send(final_message)

# Command to list youtube channels added. If there are more than 15 channels, it will paginate the list.
@bot.command()
async def list_youtube_channels(ctx):
    """Command to list youtube channels added. If there are more than 15 channels, it will paginate the list.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
    """
    entries = await asyncio.to_thread(m_config[ctx.guild.id].list_youtube_channels, ctx.guild.id, ctx.channel.id, m_database, m_yggdrasil)
    if not entries:
        await ctx.send(f"No youtube channels stored yet.")
        return
    channels = [name if watched else f"{name} ⚠️ not watched by Yggdrasil" for name, _id, watched in entries]

    page_size = 15  # number of channels per page
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
async def add_player_1(ctx, *players: str):
    """Command to add player to the list of players to search for in the videos.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
        player (str, optional): The player to be added. Defaults to None.
    """
    if not players:
        await ctx.send(f"No player(s) set.")
        return
    
    if ctx.guild.id in m_guild_tasks and ctx.channel.id in m_guild_tasks[ctx.guild.id] and "video_gathering_task" in m_guild_tasks[ctx.guild.id][ctx.channel.id]:
        await ctx.send(f"Cannot add player while video gathering is in progress. Please stop the video gathering task with !stop_video_gathering command, add the player and then start the video gathering again with !get_old_videos command.")
        return
    
    added_players = []
    repeated_players = []
    for player in players:
        state = m_config[ctx.guild.id].add_player_1(ctx.guild.id, ctx.channel.id, player, m_database)
        if "already" in state.lower():
            repeated_players.append(player)
        else:
            added_players.append(player)
    
    # Merge the messages for added players and repeated players into one message to avoid spamming the channel with multiple messages if multiple players are added at once.
    final_message = ""
    if added_players:
        final_message += f"Player(s) '{', '.join(added_players)}' stored for search!\n"
    if repeated_players:
        final_message += f"Player(s) '{', '.join(repeated_players)}' were already in the list.\n"
    await ctx.send(final_message)

# Command to add player to the list of players to search for in the videos.
# If two players are added, the bot will search for videos that have both players in the title. 
# If only one player is added, it will search for videos that have that player in the title.
@bot.command()
async def add_player_2(ctx, *players: str):
    """Command to add player to the list of players to search for in the videos.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
        player (str, optional): The player to be added. Defaults to None.
    """
    if not players:
        await ctx.send(f"No player(s) set.")
        return
    
    if ctx.guild.id in m_guild_tasks and ctx.channel.id in m_guild_tasks[ctx.guild.id] and "video_gathering_task" in m_guild_tasks[ctx.guild.id][ctx.channel.id]:
        await ctx.send(f"Cannot add player while video gathering is in progress. Please stop the video gathering task with !stop_video_gathering command, add the player and then start the video gathering again with !get_old_videos command.")
        return
    
    added_players = []
    repeated_players = []
    for player in players:
        state = m_config[ctx.guild.id].add_player_2(ctx.guild.id, ctx.channel.id, player, m_database)
        if "already" in state.lower():
            repeated_players.append(player)
        else:
            added_players.append(player)
    
    # Merge the messages for added players and repeated players into one message to avoid spamming the channel with multiple messages if multiple players are added at once.
    final_message = ""
    if added_players:
        final_message += f"Player(s) '{', '.join(added_players)}' stored for search!\n"
    if repeated_players:
        final_message += f"Player(s) '{', '.join(repeated_players)}' were already in the list.\n"
    await ctx.send(final_message)

# Command to remove player from the list of players to search for in the videos.
@bot.command()
async def remove_player_1(ctx, *players: str):
    """Command to remove player from the list of players to search for in the videos.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
        player (str, optional): The player to be removed. Defaults to None.
    """
    if not players:
        await ctx.send(f"No player(s) set.")
        return

    if ctx.guild.id in m_guild_tasks and ctx.channel.id in m_guild_tasks[ctx.guild.id] and "video_gathering_task" in m_guild_tasks[ctx.guild.id][ctx.channel.id]:
        await ctx.send(f"Cannot remove player while video gathering is in progress. Please stop the video gathering task with !stop_video_gathering command, remove the player and then start the video gathering again with !get_old_videos command.")
        return 
        
    removed_players = []
    missing_players = []
    for player in players:
        state = m_config[ctx.guild.id].remove_player_1(ctx.guild.id, ctx.channel.id, player, m_database)
        if "removed" in state.lower():
            removed_players.append(player)
        elif "not found" in state.lower():
            missing_players.append(player)
    
    # Merge the messages for removed players and missing players into one message to avoid spamming the channel with multiple messages if multiple players are removed at once.
    final_message = ""
    if removed_players:
        final_message += f"Player(s) '{', '.join(removed_players)}' removed from search!\n"
    if missing_players:
        final_message += f"Player(s) '{', '.join(missing_players)}' were not found in the list.\n"
    await ctx.send(final_message)

# Command to remove player from the list of players to search for in the videos.  
@bot.command()
async def remove_player_2(ctx, *players: str):
    """Command to remove player from the list of players to search for in the videos.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
        player (str, optional): The player to be removed. Defaults to None.
    """
    if not players:
        await ctx.send(f"No player(s) set.")
        return

    if ctx.guild.id in m_guild_tasks and ctx.channel.id in m_guild_tasks[ctx.guild.id] and "video_gathering_task" in m_guild_tasks[ctx.guild.id][ctx.channel.id]:
        await ctx.send(f"Cannot remove player while video gathering is in progress. Please stop the video gathering task with !stop_video_gathering command, remove the player and then start the video gathering again with !get_old_videos command.")
        return
    
    removed_players = []
    missing_players = []
    for player in players:
        state = m_config[ctx.guild.id].remove_player_2(ctx.guild.id, ctx.channel.id, player, m_database)
        if "removed" in state.lower():
            removed_players.append(player)
        elif "not found" in state.lower():
            missing_players.append(player)
    
    # Merge the messages for removed players and missing players into one message to avoid spamming the channel with multiple messages if multiple players are removed at once.
    final_message = ""
    if removed_players:
        final_message += f"Player(s) '{', '.join(removed_players)}' removed from search!\n"
    if missing_players:
        final_message += f"Player(s) '{', '.join(missing_players)}' were not found in the list.\n"
    await ctx.send(final_message)

@bot.command()
async def enforce_player_1(ctx, state: str):
    """Command to enforce that player 1 is in the title of the video.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
        state (str): on/off to enable or disable enforcing player 1 in the title of the video.
    """
    if state.lower() not in ["on", "off"]:
        await ctx.send(f"Invalid state '{state}'. Please provide 'on' or 'off'.")
        return
    
    m_config[ctx.guild.id].enforce_player_1(ctx.guild.id, ctx.channel.id, state.lower() == "on", m_database)
    await ctx.send(f"Enforcing player 1 in video titles {'enabled' if state.lower() == 'on' else 'disabled'}.")
    
@bot.command()
async def enforce_player_2(ctx, state: str):
    """Command to enforce that player 2 is in the title of the video.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
        state (str): on/off to enable or disable enforcing player 2 in the title of the video.
    """
    if state.lower() not in ["on", "off"]:
        await ctx.send(f"Invalid state '{state}'. Please provide 'on' or 'off'.")
        return
    
    m_config[ctx.guild.id].enforce_player_2(ctx.guild.id, ctx.channel.id, state.lower() == "on", m_database)
    await ctx.send(f"Enforcing player 2 in video titles {'enabled' if state.lower() == 'on' else 'disabled'}.")


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
    
    # Check if there is already a video gathering task running for the channel, if there is, return an error message. Otherwise, create a new task to gather videos and store it in the global variable.
    if ctx.guild.id in m_guild_tasks and ctx.channel.id in m_guild_tasks[ctx.guild.id] and "video_gathering_task" in m_guild_tasks[ctx.guild.id][ctx.channel.id]:
        await ctx.send(f"Video gathering is already in progress for this channel. Please wait for it to finish or stop it with !stop_video_gathering command before starting a new one.")
        return
    
    elif ctx.guild.id not in m_guild_tasks:
        m_guild_tasks[ctx.guild.id] = {}
        if ctx.channel.id not in m_guild_tasks[ctx.guild.id]:
            m_guild_tasks[ctx.guild.id][ctx.channel.id] = {}
    
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
    
    m_config[ctx.guild.id].set_enforce_characters(ctx.guild.id, ctx.channel.id, state, m_database)
    await ctx.send(f"Enforce characters set to '{state}'")
    
@bot.command()
async def update_frequently(ctx):
    """Command to enable automatic updates for a channel. This will make the bot search for new videos every 15 minutes 
    and send them to the channel.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
    """
    if (ctx.guild.id, ctx.channel.id) in m_database.list_auto_update_channels():
        await ctx.send("Automatic updates are already enabled for this channel. Stop them with !stop_updates.")
        return
    m_config[ctx.guild.id].targets(ctx.guild.id, [ctx.channel.id], m_database)  # makes sure the channel row exists
    m_database.set_auto_update(ctx.guild.id, ctx.channel.id, True)  # persisted: survives restarts
    if not vod_sync_loop.is_running():
        vod_sync_loop.start()
    await ctx.send(f"Automatic updates enabled for this channel (checked every {SYNC_MINUTES} minutes).")
    
@bot.command()
async def stop_updates(ctx):
    """Stops automatic updates for a channel.

    Args:
        ctx (_type_): context of the command, used to get the guild and channel id to get the config and database for that channel.
    """
    if (ctx.guild.id, ctx.channel.id) not in m_database.list_auto_update_channels():
        await ctx.send("Automatic updates are not enabled for this channel.")
        return
    m_database.set_auto_update(ctx.guild.id, ctx.channel.id, False)
    await ctx.send("Automatic updates stopped for this channel.")

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
        name="📺 !add_character_1 [charactername(s)] / !add_character_2 [charactername(s)] ",
        value="Adds character(s) to search for player 1 / player 2. You have to add the character in English, but in the search it will use its name in different languages. You can add multiple characters at once by separating them with a space (e.g. !add_character_1 Mario Luigi Peach). Characters with spaces in their names should be added with "" instead of spaces (e.g. Mr. Game & Watch should be added as \"Mr. Game & Watch\").",
        inline=False
    )
    
    embed.add_field(
        name="📺 !remove_character_1 [charactername(s)] / !remove_character_2 [charactername(s)]",
        value="Removes character(s) to search for player 1 / player 2. You have to add the character in English, but in the search it will use its name in different languages. You can remove multiple characters at once by separating them with a space (e.g. !remove_character_1 Mario Luigi Peach). Characters with spaces in their names should be removed with "" instead of spaces (e.g. Mr. Game & Watch should be removed as \"Mr. Game & Watch\").",
        inline=False
    )
    
    embed.add_field(
        name="📺 !enforce_character_1 / !enforce_character_2",
        value="Enables or disables enforcing that the character is in the title of the video. Some videos won't have characters on the title, so its useful in case you are searching for match ups with players and characters and some videos specify which characters are being played and others not",
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
        name="📺 !add_player_1 [playername(s)] / !add_player_2 [playername(s)]",
        value="Adds player(s) to search for player 1 / player 2. You can add multiple players at once by separating them with a space (e.g. !add_player_1 MKLeo Tweek Zackray)",
        inline=False
    )
    
    embed.add_field(
        name="📺 !remove_player_1 [playername(s)] / !remove_player_2 [playername(s)]",
        value="Removes player(s) to search for player 1 / player 2. You can remove multiple players at once by separating them with a space (e.g. !remove_player_1 MKLeo Tweek Zackray)",
        inline=False
    )
    
    embed.add_field(
        name="📺 !enforce_player_1 / !enforce_player_2",
        value="Enables or disables enforcing that the player is in the title of the video. This is useful for example, if you want to search VODs for a match up between two players, but only make sure that one of them is in the title of the video. This will allow to search (if characters are set) for videos that have the character and at least one of the player names (if enforced)",
        inline=False
    )
    
    embed.add_field(
        name="📺 !list_players",
        value="Lists the players you added for player 1 and player 2 in this channel",
        inline=False
    )

    embed.add_field(
        name="📺 !add_youtube_channel [ID]",
        value="Adds youtube channel(s) to the list of channels to get vods from. A default list is already provided with big channels. You can add a channel by its ID (starting with UC) or by its @name. If you add it by @name, the bot will search for the channel and add it if it finds it. You can add multiple channels at once by separating them with a space (e.g. !add_youtube_channel @channel1 @channel2 UCchannelID)",
        inline=False
    )
    
    embed.add_field(
        name="📺 !remove_youtube_channel [Name]",
        value="Removes youtube channel(s) from the list of channels to get vods from. Use !list_youtube_channels to see the list of channels you added. Removing is done by channel names. You can remove multiple channels at once by separating them with a space (e.g. !remove_youtube_channel channel1 channel2)",
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