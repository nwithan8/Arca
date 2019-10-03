#!/usr/bin/python3

import discord
from discord.ext import commands
import sys, traceback, os

PREFIX="*"

bot = commands.Bot(command_prefix=PREFIX, case_insensitive=False)

formatter = commands.HelpCommand(show_check_failure=False)

exts = [
#"espn.__init__",
"espn.__initdemo__",
"plex.__init__",
#"core.manager",
#"plex_manager.__init__",
#"jellyfin_manager.__init__"
#"emby_manager.__init__",
#"news.__init__"
#"crashy.__init__"
#"MARTA.__inittest__"
#"MARTA.__init__"
]

for ext in exts:
    bot.load_extension(ext)

@bot.event
async def on_ready():
    print(f'\n\nLogged in as : {bot.user.name} - {bot.user.id}\nVersion: {discord.__version__}\n')
    await bot.change_presence(status=discord.Status.idle,activity=discord.Game(name=f'the waiting game | {PREFIX}'))
    print(f'Successfully logged in and booted...!\n')

bot.run(os.environ.get("DISCORD_BOT_TOKEN"))
