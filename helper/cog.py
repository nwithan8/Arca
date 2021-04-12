from discord import Embed
from discord.ext import commands

from helper import discord_helper


class BasicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print(f"{self.__class__.__name__} ready to go.")

    async def respond(self, item, ctx: commands.Context):
        if type(item) == Embed:
            await ctx.send(embed=item)
        else:
            await ctx.send(item)

    async def what_subcommand(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await self.respond("What subcommand?", ctx=ctx)

    async def generic_error(self, ctx: commands.Context, error):
        print(error)
        await discord_helper.something_went_wrong(ctx=ctx)