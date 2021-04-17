from discord.ext import commands

from helper.cog import BasicCog
from helper.multi_server_handler import load_api


class UpgradeChat(BasicCog):
    def __init__(self, bot):
        super().__init__(bot)

    @commands.group(name="upgradeChat", aliases=["uc", "UC"], pass_context=True)
    async def uc(self, ctx: commands.Context):
        """
        Upgrade.Chat admin commands
        """
        await self.what_subcommand(ctx=ctx)

    @uc.command(name="users", pass_context=True)
    async def uc_users(self, ctx: commands.Context):
        api = load_api(ctx=ctx, api_type="upgradeChat")
        users = api.users
        if users:
            await self.respond(f"There are {len(users.data)} users", ctx=ctx)
        else:
            await self.respond(f"There are no users.", ctx=ctx)


def setup(bot):
    bot.add_cog(UpgradeChat(bot))