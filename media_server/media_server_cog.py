from typing import Union

import discord
from discord.ext import commands

from helper import utils
from helper.cog import BasicCog
from helper.multi_server_handler import load_api
from media_server.plex import settings as plex_settings
from media_server.jellyfin import settings as jellyfin_settings
from media_server.emby import settings as emby_settings


class MediaServerCog(BasicCog):
    def __init__(self, bot):
        super().__init__(bot)

    def get_api(self, ctx: commands.Context):
        class_name = self.__class__.__name__
        if class_name == "PlexManager":
            return load_api(ctx=ctx, api_type="plex")
        elif class_name == "JellyfinManager":
            return load_api(ctx=ctx, api_type="jellyfin")
        elif class_name == "EmbyManager":
            return load_api(ctx=ctx, api_type="emby")
        else:
            return None

    def get_settings(self):
        class_name = self.__class__.__name__
        if class_name == "PlexManager":
            return plex_settings
        elif class_name == "JellyfinManager":
            return jellyfin_settings
        elif class_name == "EmbyManager":
            return emby_settings
        else:
            return None

    def check_blacklist(self, ctx: commands.Context, discord_id: int = None,
                        username: str = None) -> utils.StatusResponse:
        to_check = []
        if discord_id:
            to_check.append(discord_id)
        if username:
            to_check.append(username)
        if not to_check:
            return utils.StatusResponse(success=False)

        api = self.get_api(ctx=ctx)
        settings = self.get_settings()

        if settings.ENABLE_BLACKLIST and api.database.on_blacklist(names_and_ids=to_check):
            return utils.StatusResponse(success=True, issue="User is on blacklist")
        return utils.StatusResponse(success=False)

    @commands.group(name="blacklist", aliases=['block'], pass_context=True)
    async def blacklist(self, ctx: commands.Context):
        await self.what_subcommand(ctx=ctx)

    @blacklist.command(name="add", aliases=["new"], pass_context=True)
    async def blacklist_add(self, ctx: commands.Context,
                            discord_user_or_media_server_username: Union[discord.Member, discord.User, str]):
        """
        Add a username or Discord ID to the blacklist
        """
        api = self.get_api(ctx=ctx)

        if isinstance(discord_user_or_media_server_username, (discord.Member, discord.User)):
            _id = discord_user_or_media_server_username.id
        else:
            _id = discord_user_or_media_server_username

        if api.database.add_to_blacklist(name_or_id=_id):
            await ctx.send("User added to blacklist.")
        else:
            await ctx.send("Something went wrong while adding that user to the blacklist.")

    @blacklist_add.error
    async def blacklist_add_error(self, ctx: commands.Context, error):
        print(error)
        await self.generic_error(ctx=ctx, error=error)

    @blacklist.command(name="remove", aliases=["delete"], pass_context=True)
    async def blacklist_remove(self, ctx: commands.Context,
                               discord_user_or_media_server_username: Union[discord.Member, discord.User, str]):
        """
        Remove a username or Discord ID from the blacklist
        """
        api = self.get_api(ctx=ctx)

        if isinstance(discord_user_or_media_server_username, (discord.Member, discord.User)):
            _id = discord_user_or_media_server_username.id
        else:
            _id = discord_user_or_media_server_username

        if api.database.remove_from_blacklist(name_or_id=_id):
            await ctx.send("User removed from blacklist.")
        else:
            await ctx.send("Something went wrong while removing that user from the blacklist.")

    @blacklist_remove.error
    async def blacklist_remove_error(self, ctx: commands.Context, error):
        print(error)
        await self.generic_error(ctx=ctx, error=error)

    @blacklist.command(name="list", pass_context=True)
    async def blacklist_list(self, ctx: commands.Context):
        """
        List the usernames on the blacklist
        """
        api = self.get_api(ctx=ctx)

        await ctx.send(
            "Blacklist entries:\n" + '\n'.join([entry.IDorUsername for entry in api.database.blacklist]))

    @blacklist_list.error
    async def blacklist_list_error(self, ctx: commands.Context, error):
        print(error)
        await self.generic_error(ctx=ctx, error=error)
