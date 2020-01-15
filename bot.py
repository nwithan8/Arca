#!/usr/bin/python3

import discord
from discord.ext import commands
import sys, traceback, os

PREFIX="*"

bot = commands.Bot(command_prefix=PREFIX)

formatter = commands.HelpCommand(show_check_failure=False)

exts = [
#"espn.__init__",
"plex.__init_plex__",
#"core.manager",
#"plex_manager_nodb.__init__",
#"plex_manager.__init__",
#"jellyfin_manager.__init__",
#"emby_manager.__init__",
#"news.__init__",
#"MARTA.__init__",
#"booksonic.__init__",
#"roles.__init__",
#"yahoofantasy.__init__",
#"smart_home.sengled_lights.__init__",
#"smart_home.google_home.__init__",
#"smart_home.wink.__init__",
#"general.__init__",
]

for ext in exts:
    bot.load_extension(ext)

@bot.event
async def on_ready():
    print(f'\n\nLogged in as : {bot.user.name} - {bot.user.id}\nVersion: {discord.__version__}\n')
    await bot.change_presence(status=discord.Status.idle,activity=discord.Game(name=f'the waiting game | {PREFIX}'))
    print(f'Successfully logged in and booted...!\n')

print("nwithan8-cogs  Copyright (C) 2019  Nathan Harris\nThis program comes with ABSOLUTELY NO WARRANTY; for details type `show w'.\nThis is free software, and you are welcome to redistribute it\nunder certain conditions; type `show c' for details.")
bot.run(os.environ.get("DISCORD_BOT_TOKEN"))
