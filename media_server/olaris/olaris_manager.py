"""
Interact with a Olaris Media Server, manage users
Copyright (C) 2020 Nathan Harris
"""

import discord
from discord.ext import commands, tasks
import json
import random
import string
import csv
from datetime import datetime
from media_server.olaris import settings as settings
from media_server.olaris import olaris_api as olaris
from helper.db_commands import DB
from helper.pastebin import hastebin, privatebin
import helper.discord_helper as discord_helper


class OlarisManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("Olaris Manager ready to go.")


def setup(bot):
    bot.add_cog(OlarisManager(bot))
