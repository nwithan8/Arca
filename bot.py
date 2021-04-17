#!/usr/bin/python3

# import helper.log as log
import discord
from discord.ext import commands
import helper.cog_handler as cog_handler
from helper.multi_server_handler import get_bot_prefix
from settings import global_settings
from database.arca.arca_database import ArcaSettingsDatabase

bot = commands.Bot(command_prefix=get_bot_prefix)
database = ArcaSettingsDatabase(sqlite_file=global_settings.SETTINGS_DATABASE_PATH, encrypted=False)
setattr(bot, 'settings_database', database)

formatter = commands.HelpCommand(show_check_failure=False)

bot.load_extension("helper.cog_handler")  # Always enabled, never disabled

extensions = global_settings.EXTENSIONS
for ext in extensions:
    path = cog_handler.find_cog_path_by_name(ext)
    if path:
        # log.info(f"Loading {path}...")
        print(f"Loading {path}...")
        bot.load_extension(path)


@bot.event
async def on_ready():
    print(f'\n\nLogged in as : {bot.user.name} - {bot.user.id}\nVersion: {discord.__version__}\n')
    await bot.change_presence(status=discord.Status.idle, activity=discord.Game(name=f'the waiting game'))
    print(f'Successfully logged in and booted...!\n')


print("Arca Copyright (C) 2021  Nathan Harris\n"
      "This program comes with ABSOLUTELY NO WARRANTY\n"
      "This is free software, and you are welcome to redistribute it under certain conditions.")

bot.run(global_settings.BOT_TOKEN)
