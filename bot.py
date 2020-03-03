#!/usr/bin/python3

import discord
from discord.ext import commands
import sys, traceback, os
import helper.cog_handler as cog_handler

PREFIX = "*"
USE_REMOTE_CONFIG = False
# True: Load cogs from a remote "cogs.txt" file in Dropbox (will need to know folder.__init__ of each)
# False: Load cogs from the ext list below.

bot = commands.Bot(command_prefix=PREFIX)

formatter = commands.HelpCommand(show_check_failure=False)

exts = [
    # "sports.espn.espn",
    # "media_server.plex.plex",
    # "media_server.plex.plex_manager",
    # "media_server.plex.plex_namanger_nodb",
    # "core.manager",
    # "media_server.jellyfin.jellyfin",
    # "media_server.emby.emby",
    # "news.news",
    # "MARTA.marta",
    # "media_server.booksonic.booksonic",
    # "discord.roles.roles",
    # "sports.yahoofantasy.yahoofantasy",
    # "smart_home.sengled_lights.sengled",
    # "smart_home.google_home.google_home",
    # "smart_home.wink.wink",
    # "general.coronavirus",
    # "general.speedtest",
    # "general.__init__"
]

if USE_REMOTE_CONFIG:
    exts = cog_handler.load_remote_config("cogs.txt")
for ext in exts:
    bot.load_extension(ext)
bot.load_extension("helper.cog_handler")


@bot.event
async def on_ready():
    print(f'\n\nLogged in as : {bot.user.name} - {bot.user.id}\nVersion: {discord.__version__}\n')
    await bot.change_presence(status=discord.Status.idle, activity=discord.Game(name=f'the waiting game | {PREFIX}'))
    print(f'Successfully logged in and booted...!\n')


print("Arca Copyright (C) 2020  Nathan Harris\nThis program comes with ABSOLUTELY NO WARRANTY\nThis is free "
      "software, and you are welcome to redistribute it\nunder certain conditions.")
bot.run(os.environ.get("DISCORD_BOT_TOKEN"))
