#!/usr/bin/python3

import os
import discord
from discord.ext import commands
import helper.cog_handler as cog_handler

PREFIX = "*"
USE_DROPBOX = False
# True: Can download/upload cogs from Dropbox
# False: Cogs have to be local
USE_REMOTE_CONFIG = False
# True: Load/store cogs from a remote "cogs.txt" file in Dropbox (will need to know folder.file of each)
# False: Load cogs from the ext list below.

bot = commands.Bot(command_prefix=PREFIX)

formatter = commands.HelpCommand(show_check_failure=False)

exts = [
    # "media_server.plex.plex",
    # "media_server.plex.plex_manager",
    # "media_server.plex.plex_namanger_nodb",
    # "media_server.olaris.olaris_manager",
    # "media_server.jellyfin.jellyfin_manager",
    # "media_server.emby.emby_manager",
    # "media_server.booksonic.booksonic",
    # "media_server.rclone.rclone",
    # "news.news",
    # "MARTA.marta",
    # "discord.roles.roles",
    # "core.manager",
    # "sports.espn.espn",
    # "sports.yahoofantasy.yahoofantasy",
    # "smart_home.sengled_lights.sengled",
    # "smart_home.google_home.google_home",
    # "smart_home.wink.wink",
    # "general.coronavirus",
    # "general.speedtest",
    # "discord_cogs.__init__",
]
if USE_REMOTE_CONFIG:
    USE_DROPBOX = True
    # You can only use cog_handler if you fill out the DROPBOX_API_KEY environmental variable
    cog_handler.USE_REMOTE_CONFIG = True
    exts = cog_handler.load_remote_config("cogs.txt")
for ext in exts:
    bot.load_extension(ext)
if USE_DROPBOX:
    cog_handler.USE_DROPBOX = True  # USE_DROPBOX has to be enabled for remote config to work
bot.load_extension("helper.cog_handler")


@bot.event
async def on_ready():
    print(f'\n\nLogged in as : {bot.user.name} - {bot.user.id}\nVersion: {discord.__version__}\n')
    await bot.change_presence(status=discord.Status.idle, activity=discord.Game(name=f'the waiting game | {PREFIX}'))
    print(f'Successfully logged in and booted...!\n')


print("Arca Copyright (C) 2020  Nathan Harris\nThis program comes with ABSOLUTELY NO WARRANTY\nThis is free "
      "software, and you are welcome to redistribute it\nunder certain conditions.")
bot.run(os.environ.get("DISCORD_BOT_TOKEN"))
