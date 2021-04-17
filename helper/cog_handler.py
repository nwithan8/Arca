from typing import List

from discord.ext import commands

from helper import cog_list
from helper.cog import BasicCog
from settings.global_settings import EXTENSIONS

def find_cog_path_by_name(cog: str):
    for k, v in cog_list.nicks_to_paths.items():
        if k == cog:
            return v
    return None

def get_cog_name(cog):
    return cog.qualified_name


class CogHandler(BasicCog):
    def __init__(self, bot):
        super().__init__(bot)

    @property
    def bot_cogs(self) -> dict:
        return self.bot.cogs

    @property
    def cog_names(self):
        return self.bot_cogs.keys()

    def get_cog_by_name(self, cog_name: str):
        return self.bot_cogs.get(cog_name, None)

    @commands.command(name="enable", aliases=["load", "activate"])
    async def cogs_enable(self, ctx: commands.Context, cog_name: str):
        """
        Enable a cog for this guild
        """
        cog = self.get_cog_by_name(cog_name)

        if not cog:
            await self.respond(f"{cog_name} is not a valid cog.", ctx=ctx)

        cog_name = get_cog_name(cog=cog)
        if self.bot.settings_database.enable_cog(cog_name=cog_name, discord_server_id=ctx.message.guild.id):
            await self.respond(f"{cog_name} has been enabled for this guild.", ctx=ctx)

    @commands.command(name="disable", aliases=["unload", "deactivate"])
    async def cogs_disable(self, ctx: commands.Context, cog_name: str):
        """
        Disable a cog for this guild
        """
        cog = self.get_cog_by_name(cog_name)

        if not cog:
            await self.respond(f"{cog_name} is not a valid cog.", ctx=ctx)

        cog_name = get_cog_name(cog=cog)
        if self.bot.settings_database.disable_cog(cog_name=cog_name, discord_server_id=ctx.message.guild.id):
            await self.respond(f"{cog_name} has been disabled for this guild.", ctx=ctx)

    @commands.group(name="cogs", aliases=["extensions"], pass_context=True)
    async def cogs(self, ctx: commands.Context):
        """
        Cogs info
        """
        await self.what_subcommand(ctx=ctx)

    @cogs.command(name="active", pass_context=True)
    async def cogs_active(self, ctx: commands.Context):
        """
        List active cogs for this guild
        """
        enabled_cogs = self.bot.settings_database.get_enabled_cogs_names(discord_server_id=ctx.message.guild.id)
        message = "\n".join(enabled_cogs)
        if message:
            await self.respond(message, ctx=ctx)
        else:
            await self.respond("There are no cogs active for this guild.", ctx=ctx)

    @cogs.command(name="all", pass_context=True)
    async def cogs_all(self, ctx: commands.Context):
        """
        List all cogs
        """
        message = "\n".join(self.cog_names)
        if message:
            await self.respond(message, ctx=ctx)
        else:
            await self.respond("There are no cogs available.", ctx=ctx)



def setup(bot):
    bot.add_cog(CogHandler(bot))
