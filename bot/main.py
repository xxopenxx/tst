import asyncio
import os
import warnings

import nextcord
from nextcord.ext import commands

import sys
sys.path.append(".")
from api.config import bot_data

warnings.filterwarnings("ignore")

bot = commands.Bot(command_prefix="!fdfdafkjabsdfa", intents=nextcord.Intents.all())


async def presence_loop():
    while True:
        await bot.change_presence(activity=nextcord.Game(name="Shard API"))
        await asyncio.sleep(5)
        await bot.change_presence(activity=nextcord.Game(name="/get-key"))
        await asyncio.sleep(5)


@bot.event
async def on_ready():
    print("Bot is up!")
    await presence_loop()


for file in os.listdir(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "cogs"))
):
    if file.endswith(".py"):
        bot.load_extension(f"cogs.{file[:-3]}")

bot.run(bot_data.token)