"""
Interact with a Olaris Media Server, manage users
Copyright (C) 2020 Nathan Harris
"""

from discord.ext import commands


class OlarisManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("Olaris Manager ready to go.")


def setup(bot):
    bot.add_cog(OlarisManager(bot))
