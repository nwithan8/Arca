"""
Configure Arca
Copyright (C) 2020 Nathan Harris
"""
import discord
from discord.ext import commands, tasks
from discord.utils import get, find
import requests
import random
import hashlib
import os
import asyncio
import helper.multi_server_helper as msh
import helper.db_commands as db
import helper.helper_functions as help
import json


async def normalize_guild_id(guild_id_or_name, bot_instance, ctx):
    if not help.is_positive_int(guild_id_or_name):  # name, not id
        guild = msh.get_guild_from_name(guild_name=guild_id_or_name, bot_instance=bot_instance)
        if guild:
            return guild.id, guild
    else:
        guild = bot_instance.get_guild(int(guild_id_or_name))
        if guild:
            return guild.id, guild
    await ctx.send("I couldn't find that Discord server. Have I been invited?")
    return None, None


def in_dm():
    def predicate(ctx):
        return isinstance(ctx.channel, discord.DMChannel)

    return commands.check(predicate)


async def set_up_config(ctx, guild_id, bot_instance):
    await ctx.send("Setting up the new Discord server...")
    guild_id_int = None
    if not isinstance(guild_id, int):
        guild = msh.get_guild_from_name(guild_name=guild_id, bot_instance=bot_instance)
        if guild:
            guild_id_int = guild.id
    else:
        guild_id_int = guild_id
    if guild_id_int:
        if msh.create_listing(guild_id=guild_id_int):
            await ctx.send("Your Discord server configuration was successfully created.")
            return True
        else:
            await ctx.send('Sorry, was unable to set up your Discord server configuration.')
    else:
        await ctx.send("Sorry, I couldn't find that Discord server. Have I been invited?")
    return False


class Configure(commands.Cog):

    @commands.group(aliases=["configure", "setup"], pass_context=True)
    async def config(self, ctx: commands.Context):
        """
        Configure Arca
        """
        if not isinstance(ctx.channel, discord.DMChannel):
            await ctx.send("Send me a direct message to set up Arca.")
        elif ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")

    @in_dm()
    @config.command(aliases=['claim', 'lock'], pass_context=True)
    async def config_lock(self, ctx: commands.Context, *, guild_id_or_name: str):
        error = False
        guild_id, guild = await normalize_guild_id(guild_id_or_name=guild_id_or_name, bot_instance=self.bot, ctx=ctx)
        if not guild_id:
            error = True
        # also check that user is in the guild, so they can't claim servers they don't belong to.
        if not error:
            if not msh.user_is_member_of_guild(guild=guild, user_id=ctx.author.id):
                error = True
                await ctx.send("You can't change settings for a Discord server you don't belong to.")
        if not error:
            if msh.is_admin_set(guild_id=guild_id):
                await ctx.send(f"The configuration for {guild_id} is already locked.")
            else:
                listing_exists = True
                if not msh.listing_exists(guild_id=guild_id, table_name='servers'):
                    listing_exists = await set_up_config(ctx=ctx, guild_id=guild_id_or_name, bot_instance=self.bot)
                if listing_exists:
                    await ctx.send("Locking the Discord server configuration...")
                    if msh.set_admin(guild_id=guild_id, user_id=ctx.author.id):
                        await ctx.send(
                            "Your Discord server configuration was successfully locked. Only you can alter the "
                            "configuration in the future.")
                    else:
                        await ctx.send("Your Discord server configuration could not be locked.")
        else:
            await ctx.send("I couldn't find that Discord server. Have I been invited?")

    @in_dm()
    @config.command(aliases=['current', 'list', 'settings'], pass_context=True)
    async def config_current(self, ctx: commands.Context, guild_id_or_name: str, cog_name: str = None):
        guild_id, guild = await normalize_guild_id(guild_id_or_name=guild_id_or_name, bot_instance=self.bot, ctx=ctx)
        if guild_id:
            if msh.is_admin_dm_check(guild_id=guild_id, user_id=ctx.author.id):
                if cog_name:
                    config = msh.get_whole_media_server_config(guild_id=guild_id, server_type=cog_name)
                    columns = msh.get_table_column_names(table_name=cog_name)
                else:
                    config = msh.get_all_cogs_from_config(guild_id)
                    columns = msh.get_table_column_names(table_name='cogs')
                if not config:
                    if cog_name:
                        await ctx.send("There is no current configuration for this cog.")
                    else:
                        await ctx.send("There is no current configuration for this guild.")
                else:
                    if columns:
                        response = ''
                        for i in range(0, len(columns)):
                            value = config[0][i]
                            if value == 0 or not value:
                                value = 'False'
                            elif value == 1:
                                value = 'True'
                            response += f'**{columns[i][1]}**: {value}\n'
                        await ctx.send(response)
                    else:
                        await ctx.send("Sorry, something went wrong.")
            else:
                await ctx.send("You do not have permission to edit Arca's configuration.")

    @in_dm()
    @config.command(aliases=['vars', 'variables'], pass_context=True)
    async def config_variables(self, ctx: commands.Context, cog_name: str):
        if msh.is_valid_cog(cog_name=cog_name):
            config_json = msh.get_example_config(cog_name=cog_name)
            if config_json:
                response = ''
                for key in json.load(config_json[0]).keys():
                    response += f'**{key}**\n'
                await ctx.send(response)
            else:
                await ctx.send("Sorry, something went wrong.")
        else:
            await ctx.send("Invalid cog.")

    @in_dm()
    @config.command(aliases=['enable'], pass_context=True)
    async def config_enable(self, ctx: commands.Context, guild_id_or_name: str, cog_name: str):
        guild_id, guild = await normalize_guild_id(guild_id_or_name=guild_id_or_name, bot_instance=self.bot, ctx=ctx)
        if guild_id:
            if msh.is_admin_dm_check(guild_id=guild_id, user_id=ctx.author.id):
                if msh.is_valid_cog(cog_name=cog_name):
                    status = msh.cog_is_enabled(guild_id=guild_id, cog_name=cog_name)
                    if status or status == 'Error':
                        await ctx.send("This cog is already enabled.")
                    else:
                        proceed = True
                        if cog_name in ['Plex', 'PlexManager', 'JellyfinManager', 'EmbyManager']:
                            proceed = msh.create_discord_connector(guild_id=guild_id)
                            msh.create_cog_config(guild_id=guild_id, cog_name=cog_name)
                        if proceed:
                            result = msh.enable_cog(guild_id=guild_id, cog_name=cog_name)
                            if not result or result == 'Error':
                                await ctx.send(f"Could not enable {cog_name}.")
                            else:
                                if cog_name in ['Plex', 'PlexManager', 'JellyfinManager', 'EmbyManager']:
                                    if msh.create_discord_connector(guild_id=guild_id):
                                        await ctx.send(f"{cog_name} is enabled.")

                                else:
                                    await ctx.send(f"{cog_name} is enabled.")
                        else:
                            await ctx.send(f"Could not enable {cog_name}.")
                else:
                    await ctx.send("Invalid cog.")
            else:
                await ctx.send("You do not have permission to edit Arca's configuration.")

    @in_dm()
    @config.command(aliases=['disable'], pass_context=True)
    async def config_disable(self, ctx: commands.Context, guild_id_or_name: str, cog_name: str):
        guild_id, guild = await normalize_guild_id(guild_id_or_name=guild_id_or_name, bot_instance=self.bot, ctx=ctx)
        if guild_id:
            if msh.is_admin_dm_check(guild_id=guild_id, user_id=ctx.author.id):
                if msh.is_valid_cog(cog_name=cog_name):
                    status = msh.cog_is_enabled(guild_id=guild_id, cog_name=cog_name)
                    if not status:
                        await ctx.send("This cog is already disabled.")
                    else:
                        if status == 'Error':
                            await ctx.send(f"Could not disable {cog_name}")
                        result = msh.disable_cog(guild_id=guild_id, cog_name=cog_name)
                        if not result or result == 'Error':
                            await ctx.send(f"Could not disable {cog_name}.")
                        else:
                            await ctx.send(f"{cog_name} is disabled.")
                else:
                    await ctx.send("Invalid cog.")
            else:
                await ctx.send("You do not have permission to edit Arca's configuration.")

    @in_dm()
    @config.command(aliases=['update', 'edit'], pass_context=True)
    async def config_update(self, ctx: commands.Context, guild_id_or_name: str, cog_name: str, setting_name: str, *,
                            setting: str):
        guild_id, guild = await normalize_guild_id(guild_id_or_name=guild_id_or_name, bot_instance=self.bot, ctx=ctx)
        if guild_id:
            if msh.is_admin_dm_check(guild_id=guild_id, user_id=ctx.author.id):
                if msh.is_valid_cog(cog_name=cog_name):
                    status = msh.cog_is_enabled(guild_id=guild_id, cog_name=cog_name)
                    if not status:
                        await ctx.send("This cog is disabled.")
                    else:
                        if msh.is_valid_setting(guild_id=guild_id, setting_name=setting_name, cog_name=cog_name):
                            result = msh.edit_media_server_config(guild_id=guild_id, server_type=cog_name,
                                                                  setting_name=setting_name,
                                                                  setting_value=setting)
                            if result:
                                if result == 'Error':
                                    await ctx.send(f"Invalid type for {setting_name}.")
                                else:
                                    await ctx.send(f"{setting_name} updated for {cog_name}.")
                            else:
                                await ctx.send(f"Could not update {setting_name} for {cog_name}.")
                        else:
                            await ctx.send(f"Invalid setting. See 'config vars {guild_id} {cog_name}'.")
                else:
                    await ctx.send("Invalid cog.")
            else:
                await ctx.send("You do not have permission to edit Arca's configuration.")

    def __init__(self, bot):
        self.bot = bot
        print("Configurator ready.")


def setup(bot):
    bot.add_cog(Configure(bot))
