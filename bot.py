#!/usr/bin/python3

# import helper.log as log
import discord
from discord.ext import commands
import helper.cog_handler as cog_handler
from settings import settings as settings

bot = commands.Bot(command_prefix=settings.PREFIX)

formatter = commands.HelpCommand(show_check_failure=False)

exts = settings.extensions

if settings.USE_REMOTE_CONFIG:
    settings.USE_DROPBOX = True
    # You can only use cog_handler if you fill out the DROPBOX_API_KEY environmental variable
    cog_handler.USE_REMOTE_CONFIG = True
    exts = cog_handler.load_remote_config("cogs.txt")
for ext in exts:
    path = cog_handler.find_cog_path_by_name(ext)
    if path:
        # log.info(f"Loading {path}...")
        print(f"Loading {path}...")
        bot.load_extension(path)
if settings.USE_DROPBOX:
    cog_handler.USE_DROPBOX = True  # USE_DROPBOX has to be enabled for remote config to work
bot.load_extension("helper.cog_handler")  # Always enabled, never disabled


@bot.event
async def on_ready():
    print(f'\n\nLogged in as : {bot.user.name} - {bot.user.id}\nVersion: {discord.__version__}\n')
    await bot.change_presence(status=discord.Status.idle, activity=discord.Game(name=f'the waiting game | {settings.PREFIX}'))
    print(f'Successfully logged in and booted...!\n')


print("Arca Copyright (C) 2020  Nathan Harris\n"
      "This program comes with ABSOLUTELY NO WARRANTY\n"
      "This is free software, and you are welcome to redistribute it under certain conditions.")

bot.run(settings.BOT_TOKEN)
