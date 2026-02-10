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

m_config = config.MyConfig()

# Commands
@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong!")
    
@bot.command()
async def hello(ctx):
    await ctx.send(f"Hello {ctx.author.mention} 👋")
    
@bot.command()
async def add_character(ctx, choice: str = None):
    if not choice or choice not in config.smash_characters:
        await ctx.send(f"Choose a valid character")
        return
    
    m_config.add_character(ctx.channel.id, choice)
    await ctx.send(f"Character stored for search!")
    
@bot.command()
async def add_youtube_channel(ctx, channel: str = None):
    if not channel:
        await ctx.send(f"Provide a youtube channel (Either the ID starting with UC or the @)")
        return
    state = m_config.add_youtube_channel(ctx.channel.id, channel, youtube)
    await ctx.send(state)
    
@bot.command()
async def add_player(ctx, player: str = None):
    if not player:
        await ctx.send(f"No player set.")
        return
    state = m_config.add_player(ctx.channel.id, player)
    await ctx.send(state)
    
@bot.command()
async def get_old_videos(ctx):
    await ctx.send(f"This will take a while depending on channel history and video ammount")
    
    video_list = await asyncio.to_thread(m_config.get_old_videos, ctx.channel.id, youtube)
    for msg in video_list:
        dt = datetime.fromisoformat(msg['publishedAt'].replace("Z", "+00:00"))
        formatted_date = dt.strftime("%Y-%m-%d %H:%M")
        await ctx.send(f"{msg['title']} ({formatted_date}): {msg['url']}")
        await asyncio.sleep(3)
    
# Run bot
bot.run(DISCORD_BOT_TOKEN)