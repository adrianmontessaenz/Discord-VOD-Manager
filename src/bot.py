import os
import asyncio
from dotenv import load_dotenv
import discord
from googleapiclient.discovery import build
from discord.ext import commands
from discord import SelectOption
from datetime import datetime
import config
from typing import Literal
import json


load_dotenv()

DISCORD_BOT_TOKEN=os.getenv("DISCORD_BOT_TOKEN")
YOUTUBE_API_KEY=os.getenv("YOUTUBE_API_KEY")

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

bot.remove_command("help")

m_config = {}
m_guild_tasks = {}

# ------------- Events -------------
# Initialize bot and global info
@bot.event
async def on_ready():
    file_json = {}
    if os.path.exists('data/config.json'):
        with open('data/config.json', 'r') as file:
            file_json = json.load(file)
    config.smash_characters = file_json["char_names"]


# Show welcome message and create memory for the server
@bot.event
async def on_guild_join(guild):
    # Optional: send a welcome message
    if guild.text_channels[0].permissions_for(guild.me).send_messages:
        await guild.text_channels[0].send(
            "👋 Hi! Thanks for inviting me.\n"
            "Type `!help` to see what I can do."
        )
    
    # Create configuration for this server
    m_config[guild.id] = config.MyConfig()
    
# Remove tasks from guild and remove memory stored for it.
@bot.event
async def on_guild_remove(guild):
    task = m_guild_tasks.pop(guild.id, None)
    if task:
        task.cancel()
    m_config.pop(guild.id)    
    
# Remove tasks from guild and remove memory stored for it.
# This is in case the channel is deleted, so the bot doesn't keep history and tasks for channels that don't exist anymore.
@bot.event
async def on_guild_channel_delete(channel):
    if channel.guild.id in m_guild_tasks:
        task = m_guild_tasks[channel.guild.id]
        task.cancel()
        m_guild_tasks.pop(channel.guild.id)
    if channel.guild.id in m_config:
        m_config.pop(channel.guild.id)


# ------------- Commands -------------
# Simple command to test the bot is working and responding 
@bot.command()
async def hello(ctx):
    await ctx.send(f"Hello {ctx.author.mention} 👋")

# Command to add character to the list of characters to search for in the videos.
@bot.command()
async def add_character_1(ctx, choice: str = None):
    if not choice or choice not in config.smash_characters.keys():
        await ctx.send(f"Choose a valid character")
        return
    
    m_config.add_character_1(ctx.channel.id, choice)
    await ctx.send(f"Character stored for search!")

# Command to add character to the list of characters to search for in the videos.
# If two characters are added, the bot will search for videos that have both characters in the title.
# If only one character is added, it will search for videos that have that character in the title.
@bot.command()
async def add_character_2(ctx, choice: str = None):
    if not choice or choice not in config.smash_characters:
        await ctx.send(f"Choose a valid character")
        return
    
    m_config.add_character_2(ctx.channel.id, choice)
    await ctx.send(f"Character stored for search!")
    
# Command to remove character from the list of characters to search for in the videos.
@bot.command()
async def remove_character_1(ctx, choice: str = None):
    if not choice or choice not in config.smash_characters.keys():
        await ctx.send(f"Choose a valid character")
        return
    
    state = m_config.remove_character_1(ctx.channel.id, choice)
    await ctx.send(state)
    
# Command to remove character from the list of characters to search for in the videos.
@bot.command()
async def remove_character_2(ctx, choice: str = None):
    if not choice or choice not in config.smash_characters.keys():
        await ctx.send(f"Choose a valid character")
        return
    
    state = m_config.remove_character_2(ctx.channel.id, choice)
    await ctx.send(state)
    
@bot.command()
async def list_characters(ctx):
    chars_1 = m_config.get_characters_1(ctx.channel.id)
    chars_2 = m_config.get_characters_2(ctx.channel.id)
    
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
    if not channel:
        await ctx.send(f"Provide a youtube channel (Either the ID starting with UC or the @)")
        return
    state = m_config.add_youtube_channel(ctx.channel.id, channel, youtube)
    await ctx.send(state)
    
@bot.command()
async def remove_youtube_channel(ctx, channel: str = None):
    if not channel:
        await ctx.send(f"Provide a youtube channel name (See your list with !list_youtube_channels)")
        return
    state = m_config.remove_youtube_channel(ctx.channel.id, channel)
    await ctx.send(state)    

# Command to list youtube channels added. If there are more than 15 channels, it will paginate the list.
@bot.command()
async def list_youtube_channels(ctx):
    channels = m_config.get_youtube_channels(ctx.channel.id)
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
    if not player:
        await ctx.send(f"No player set.")
        return
    state = m_config.add_player_1(ctx.channel.id, player)
    await ctx.send(state)

# Command to add player to the list of players to search for in the videos.
# If two players are added, the bot will search for videos that have both players in the title. 
# If only one player is added, it will search for videos that have that player in the title.
@bot.command()
async def add_player_2(ctx, player: str = None):
    if not player:
        await ctx.send(f"No player set.")
        return
    state = m_config.add_player_2(ctx.channel.id, player)
    await ctx.send(state)

# Command to remove player from the list of players to search for in the videos.
@bot.command()
async def remove_player_1(ctx, player: str = None):
    if not player:
        await ctx.send(f"No player set.")
        return
    state = m_config.remove_player_1(ctx.channel.id, player)
    await ctx.send(state)

# Command to remove player from the list of players to search for in the videos.  
@bot.command()
async def remove_player_2(ctx, player: str = None):
    if not player:
        await ctx.send(f"No player set.")
        return
    state = m_config.remove_player_2(ctx.channel.id, player)
    await ctx.send(state)

# Command to list players added for player 1 and player 2.
@bot.command()
async def list_players(ctx):
    players_1 = m_config.get_players_1(ctx.channel.id)
    players_2 = m_config.get_players_2(ctx.channel.id)
    
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
async def get_old_videos(ctx):
    await ctx.send(f"This will take a while depending on channel history and video ammount")
    
    video_list = await asyncio.to_thread(m_config.get_old_videos, ctx.channel.id, youtube)
    for msg in video_list:
        dt = datetime.fromisoformat(msg['publishedAt'].replace("Z", "+00:00"))
        formatted_date = dt.strftime("%Y-%m-%d %H:%M")
        await ctx.send(f"{msg['title']} ({formatted_date}): {msg['url']}")
        await asyncio.sleep(3)
        
# Command to enforce that characters are also in the title of the videos. Some VODs don't show the name on titles, 
# so by default this is set to False, but you can set it to True if you want to enforce that the character is 
# also in the title of the videos. 
# This will make the search more strict, but it will also make sure that the videos that are sent are more relevant 
# to the characters you added.
@bot.command()
async def enforce_characters(ctx, state : bool):
    m_config.enforce_characters(ctx.channel.id, state)
    await ctx.send(f"Enforce characters set to '{state}'")
    
    
# Command to show all available commands and how to use them.
@bot.command()
async def help(ctx):
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
        name="📺 !remove_youtube_channel [ID]",
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
        name="ℹ️ !help",
        value="Shows this help message.",
        inline=False
    )

    embed.set_footer(text="Bot made to gather VODs easily and store them on Discord")

    await ctx.send(embed=embed)
    
# Run bot
bot.run(DISCORD_BOT_TOKEN)