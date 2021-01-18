"""
Interact with a Jellyfin Media Server, manage users
Copyright (C) 2019 Nathan Harris
"""
import time
from typing import Union, List
import json
import string
import random
import csv
from datetime import datetime

import asyncio
import discord
from discord.ext import commands, tasks

from media_server import multi_server_handler
import helper.discord_helper as discord_helper
import helper.utils as utils
from media_server.database.database import PlexUser, JellyfinUser, EmbyUser
from media_server.jellyfin import settings as settings
from media_server.jellyfin import jellyfin_api as jf
from media_server.jellyfin import jellyfin_stats as js
from helper.pastebin import hastebin, privatebin
from media_server.jellyfin import settings as jellyfin_settings

def get_user_entries_from_database(ctx: commands.Context, discord_id: int = None, jellyfin_username: str = None, first_only: bool = False) -> Union[List[Union[PlexUser, EmbyUser, JellyfinUser, utils.StatusResponse]], utils.StatusResponse]:
    if not discord_id and not jellyfin_username:
        raise Exception("Must provide either jellyfin_username or discord_id")

    jellyfin_api = multi_server_handler.get_jellyfin_api(ctx=ctx)

    database_user_entries = jellyfin_api.database.get_user(discord_id=discord_id, media_server_username=jellyfin_username, first_match_only=first_only)
    if not database_user_entries:
        return utils.StatusResponse(success=False, issue="User not found in database")
    return database_user_entries


def remove_user_from_database(ctx: commands.Context, user = None, discord_id: int = None, jellyfin_username: str = None) -> utils.StatusResponse:
    if not user and not discord_id and not jellyfin_username:
        raise Exception("Must provide either user, jellyfin_username or discord_id")

    jellyfin_api = multi_server_handler.get_jellyfin_api(ctx=ctx)

    if not user:
        user = jellyfin_api.database.make_user(discord_id=discord_id, jellyfin_username=jellyfin_username)
    if not jellyfin_api.database.remove_user_from_database(user=user):
        return utils.StatusResponse(success=False, issue="Could not remove user from database.")
    return utils.StatusResponse(success=True)


def check_blacklist(ctx: commands.Context, discord_id: int = None, jellyfin_username: str = None) -> utils.StatusResponse:
    to_check = []
    if discord_id:
        to_check.append(discord_id)
    if jellyfin_username:
        to_check.append(jellyfin_username)
    if not to_check:
        return utils.StatusResponse(success=False)

    jellyfin_api = multi_server_handler.get_jellyfin_api(ctx)

    if jellyfin_settings.ENABLE_BLACKLIST and jellyfin_api.database.on_blacklist(names_and_ids=to_check):
        return utils.StatusResponse(success=True, issue="User is on blacklist")
    return utils.StatusResponse(success=False)


async def add_user_to_jellyfin(ctx: commands.Context,
                               jellyfin_username: str,
                               user_type: str) -> utils.StatusResponse:
    """
    Add a user to a Jellyfin instance

    :param user_type:
    :type user_type:
    :param ctx:
    :type ctx:
    :param jellyfin_username:
    :type jellyfin_username:
    :return:
    :rtype:
    """

    jellyfin_server = multi_server_handler.get_jellyfin_api(ctx=ctx)

    try:
        response = jellyfin_server.add_user(jellyfin_username=jellyfin_username)
        if not response:
            return response
        user = response.attachment
        response = jellyfin_server.reset_password(user_id=user.id)
        if not response:
            return response
        response = jellyfin_server.set_user_password(user_id=user.id, currentPass="", newPass=utils.password(10))
        if not response:
            return response
        response = jellyfin_server.update_policy(user_id=user.id, policy=jellyfin_server.default_policy)
        if not response:
            return response
        return utils.StatusResponse(success=True, attachment=user)
    except Exception as e:
        print(e)
        return utils.StatusResponse(success=False, issue=e.__str__())


async def remove_user_from_jellyfin(ctx: commands.Context,
                                    jellyfin_username: str) -> utils.StatusResponse:
    """
    Remove a user from a single Plex instance ( + Ombi/Tautulli)

    :param ctx:
    :type ctx:
    :param jellyfin_username:
    :type jellyfin_username:
    :return:
    :rtype:
    """
    jellyfin_server = multi_server_handler.get_jellyfin_api(ctx)

    try:
        response = jellyfin_server.remove_user(jellyfin_username=jellyfin_username)
        return response
    except Exception as e:
        return utils.StatusResponse(success=False, issue=e.__str__())


async def add_to_database_add_to_jellyfin_add_role_send_dm(ctx: commands.Context,
                                                           jellyfin_username: str,
                                                           discord_id: int,
                                                           user_type: str,
                                                           role_name: str,
                                                           role_reason: str,
                                                           pay_method: str = None):
    if check_blacklist(ctx=ctx, discord_id=discord_id, jellyfin_username=jellyfin_username):
        return utils.StatusResponse(success=False, issue="USER ON BLACKLIST", code=999)

    jellyfin_api = multi_server_handler.get_jellyfin_api(ctx)

    expiration_stamp = None
    if user_type == 'Trial':
        expiration_stamp = int(time.time()) + jellyfin_settings.TRIAL_LENGTH
    new_database_entry = jellyfin_api.database.make_user(jellyfin_username=jellyfin_username,
                                                         discord_id=discord_id,
                                                         user_type=user_type,
                                                         pay_method=pay_method,
                                                         expiration_stamp=expiration_stamp)

    response = jellyfin_api.database.add_user_to_database(new_database_entry)
    if not response:
        return response

    response_or_user = await add_user_to_jellyfin(ctx=ctx, jellyfin_username=jellyfin_username, user_type=user_type)
    if not response_or_user:
        return response_or_user

    discord_user = await discord_helper.get_user(user_id=discord_id, ctx=ctx)
    if not discord_user:
        return utils.StatusResponse(success=False, issue="Could not load Discord user to modify roles.")

    if not await discord_helper.add_user_role(user=discord_user, role_name=role_name, reason=role_reason):
        return utils.StatusResponse(success=False, issue=f"Could not add {role_name} role to Discord user.")

    dm_message = _create_dm_message(server_name=jellyfin_api.server_name,
                                    server_url=jellyfin_api.url,
                                    username=jellyfin_username,
                                    password=response_or_user.attachment.password)

    await discord_helper.send_direct_message(user=discord_user, message=dm_message)

    return utils.StatusResponse(success=True)


async def add_to_database_add_role(ctx: commands.Context,
                                   jellyfin_username: str,
                                   discord_id: int,
                                   user_type: str,
                                   role_name: str,
                                   role_reason: str,
                                   pay_method: str = None):
    if check_blacklist(ctx=ctx, discord_id=discord_id, jellyfin_username=jellyfin_username):
        return utils.StatusResponse(success=False, status_code=utils.StatusCodes.USER_ON_BLACKLIST)

    jellyfin_api = multi_server_handler.get_jellyfin_api(ctx)

    new_database_entry = jellyfin_api.database.make_user(jellyfin_username=jellyfin_username,
                                                         discord_id=discord_id,
                                                         user_type=user_type,
                                                         pay_method=pay_method)

    response = jellyfin_api.database.add_user_to_database(new_database_entry)
    if not response:
        return response

    discord_user = await discord_helper.get_user(user_id=discord_id, ctx=ctx)
    if not discord_user:
        return utils.StatusResponse(success=False, issue="Could not load Discord user to modify roles.")

    if not await discord_helper.add_user_role(user=discord_user, role_name=role_name, reason=role_reason):
        return utils.StatusResponse(success=False, issue=f"Could not add {role_name} role to Discord user.")

    return utils.StatusResponse(success=True)


async def remove_from_jellyfin_remove_from_database_remove_role_send_dm(ctx: commands.Context,
                                                                        role_name: str,
                                                                        role_reason: str,
                                                                        dm_message: str,
                                                                        jellyfin_username: str = None,
                                                                        discord_id: int = None):

    database_user_entries = get_user_entries_from_database(ctx=ctx, discord_id=discord_id, jellyfin_username=jellyfin_username)
    if not database_user_entries:
        return database_user_entries # error message

    response = await remove_user_from_jellyfin(ctx=ctx, jellyfin_username=jellyfin_username)
    if not response:
        return response

    for entry in database_user_entries:
        # delete all entries in database
        response = remove_user_from_database(ctx=ctx, user=entry)
        if not response:
            return response

    discord_user = await discord_helper.get_user(user_id=database_user_entries[0].DiscordID, ctx=ctx)
    if not discord_user:
        return utils.StatusResponse(success=False, issue="Could not load Discord user to modify roles.")

    if not await discord_helper.remove_user_role(user=discord_user, role_name=role_name, reason=role_reason):
        return utils.StatusResponse(success=False, issue=f"Could not remove {role_name} role from Discord user.")

    await discord_helper.send_direct_message(user=discord_user, message=dm_message)

    return utils.StatusResponse(success=True)


async def check_trials(ctx: commands.Context):
    jellyfin_api = multi_server_handler.get_jellyfin_api(ctx=ctx)

    for trial_database_user in jellyfin_api.database.expired_trials:
        await remove_from_jellyfin_remove_from_database_remove_role_send_dm(ctx=ctx,
                                                                            role_name=jellyfin_settings.TRIAL_ROLE_NAME,
                                                                            role_reason="Trial ended.",
                                                                            dm_message="Your trial has ended.",
                                                                            jellyfin_username=trial_database_user.MediaServerUsername,
                                                                            discord_id=trial_database_user.DiscordID)


def _create_dm_message(server_name: str, server_url: str, username: str, password: str = None):
    text = f"You have been added to {server_name}!\n\n" \
           f"URL: {server_url}" \
           f"Username: {username}" \
           f"Password: {password if password else settings.NO_PASSWORD_MESSAGE}"
    return text


class JellyfinManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("Jellyfin Manager ready to go.")


    async def check_subs(self, ctx: commands.Context):
        for discord_member in discord_helper.get_users_without_roles(bot=self.bot,
                                                                     role_names=jellyfin_settings.SUB_ROLES,
                                                                     guild=ctx.message.guild):
            if discord_member.id not in jellyfin_settings.EXEMPT_SUBS:
                await remove_from_jellyfin_remove_from_database_remove_role_send_dm(ctx=ctx,
                                                                                    discord_id=discord_member.id,
                                                                                    role_name=jellyfin_settings.INVITED_ROLE,
                                                                                    role_reason="Subscription ended.",
                                                                                    dm_message=f"You have been removed from Jellyfin because your subscription has ended.")

    """
    async def purge_winners(self, ctx):
        try:
            winners = db.get_winners()
            monitorlist = []
            for u in winners:
                monitorlist.append(u[0])
            print("Winners: ")
            print(monitorlist)
            removed_list = ""
            error_message = ""
            for u in monitorlist:
                try:
                    # returns time watched in last 14 days, in seconds
                    watchtime = js.getUserHistory(user_id=str(u), past_x_days=14, sum_watch_time=True)
                    if not watchtime:
                        watchtime = 0
                    watchtime = int(watchtime)
                    if watchtime < settings.WINNER_THRESHOLD:
                        print('{} has NOT met the duration requirements. Purging...'.format(u))
                        mention_id = await self.remove_winner(str(u))
                        removed_list += (mention_id if mention_id is not None else "")
                except Exception as e:
                    print(e)
                    error_message += "Error checking {}. ".format(str(u))
                    pass
            if removed_list:
                await ctx.send("{}You have been removed as a Winner due to inactivity.".format(removed_list))
            else:
                await ctx.send("No winners purged.")
            if error_message:
                await ctx.send(error_message)
        except Exception as e:
            print(e)
            await ctx.send("Something went wrong. Please try again later.")
    
    async def remove_winner(self, jellyfinId):
        try:
            id = db.find_user_in_db(ServerOrDiscord="Discord", data=jellyfinId)
            if id is not None:
                s = remove_from_jellyfin(user_id=jellyfinId)
                if s == 200:
                    user = self.bot
                    await user.create_dm()
                    await user.dm_channel.send(
                        "You have been removed from {} due to inactivity.".format(
                            str(settings.JELLYFIN_SERVER_NICKNAME)))
                    await user.remove_roles(discord.utils.get(self.bot.get_guild(int(settings.DISCORD_SERVER_ID)).roles,
                                                              name=settings.WINNER_ROLE_NAME),
                                            reason="Inactive winner")
                    return "<@{}>, ".format(id)
        except Exception as e:
            pass
        return None

    async def check_subs(self):
        print("Checking Jellyfin subs...")
        for member in discord_helper.get_users_without_roles(bot=self.bot, roleNames=settings.SUB_ROLES,
                                                             guildID=settings.DISCORD_SERVER_ID):
            s = remove_nonsub(member.id)
            if s == 700:
                print("{} was not a past Jellyfin subscriber".format(member))
            elif s != 200:
                print("Couldn't remove {} from Jellyfin".format(member))
        print("Jellyfin subs check complete.")

    async def check_trials(self):
        print("Checking Jellyfin trials...")
        trials = db.get_trials()
        trial_role = discord.utils.get(self.bot.get_guild(int(settings.DISCORD_SERVER_ID)).roles,
                                       name=settings.TRIAL_ROLE_NAME)
        for u in trials:
            print("Ending trial for {}".format(str(u[0])))
            try:
                s = remove_from_jellyfin(user_id=int(u[0]))
                if s == 200:
                    user = self.bot.get_guild(int(settings.DISCORD_SERVER_ID))
                    await user.create_dm()
                    await user.dm_channel.send(settings.TRIAL_END_NOTIFICATION)
                    await user.remove_roles(trial_role, reason="Trial has ended.")
            except Exception as e:
                print(e)
                print("Discord user {} not found.".format(str(u[0])))
        print("Jellyfin Trials check completed.")

    @tasks.loop(hours=24)
    async def backup_database_timer(self):
        await backup_database()

    @tasks.loop(hours=settings.SUB_CHECK_TIME * 24)
    async def check_subs_timer(self):
        await self.check_subs()

    @tasks.loop(minutes=settings.TRIAL_CHECK_FREQUENCY)
    async def check_trials_timer(self):
        await self.check_trials()
    """

    @commands.group(name="jm", aliases=["JM", "JellyMan", "jellyman", "JellyfinMan", "jellyfinman", "JellyfinManager",
                                        "jellyfinmanager"], pass_context=True)
    async def jellyfin(self, ctx: commands.Context):
        """
        Jellyfin Media Server commands
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")

    @jellyfin.command(name="access", pass_context=True)
    # Anyone can use this command
    async def jellyfin_access(self, ctx: commands.Context, jellyfin_username: str = None):
        """
        Check if you or another user has access to the Jellyfin server
        """
        _jellyfin_username = jellyfin_username

        if not _jellyfin_username:
            database_user = get_user_entries_from_database(ctx=ctx, discord_id=ctx.message.author.id, first_only=True)
            if not database_user:
                message = "Could not find your Jellyfin username in the database."
            else:
                _jellyfin_username = database_user[0].MediaServerUsername

        jellyfin_api = multi_server_handler.get_jellyfin_api(ctx=ctx)

        if _jellyfin_username:
            if _jellyfin_username in [user.name for user in jellyfin_api.get_users()]:
                message = f"You have access to {jellyfin_api.server_name}"
            else:
                message = f"You do not have access to {jellyfin_api.server_name}"
        await ctx.send(message)

    @jellyfin_access.error
    async def jellyfin_access_error(self, ctx, error):
        print(error)
        await discord_helper.something_went_wrong(ctx=ctx)

    @jellyfin.command(name="blacklist", aliases=['block'], pass_context=True)
    @commands.has_role(jellyfin_settings.DISCORD_ADMIN_ROLE_NAME)
    async def jellyfin_blacklist(self, ctx: commands.Context, add_or_remove: str, discord_user_or_jellyfin_username: Union[discord.Member, discord.User, str]):
        """
        Blacklist a Jellyfin username or Discord ID
        """
        jellyfin_api = multi_server_handler.get_jellyfin_api(ctx=ctx)

        if isinstance(discord_user_or_jellyfin_username, (discord.Member, discord.User)):
            _id = discord_user_or_jellyfin_username.id
        else:
            _id = discord_user_or_jellyfin_username

        if add_or_remove.lower() == "add":
            if jellyfin_api.database.add_to_blacklist(name_or_id=_id):
                await ctx.send("User added to blacklist.")
            else:
                await ctx.send("Something went wrong while adding that user to the blacklist.")
        elif add_or_remove.lower() == 'remove':
            if jellyfin_api.database.remove_from_blacklist(name_or_id=_id):
                await ctx.send("User removed from blacklist.")
            else:
                await ctx.send("Something went wrong while removing user from the blacklist.")
        elif add_or_remove.lower() == 'list':
            await ctx.send("Blacklist entries:\n" + '\n'.join([entry.IDorUsername for entry in jellyfin_api.database.blacklist]))
        else:
            await ctx.send("Invalid blacklist action.")

    @jellyfin_blacklist.error
    async def jellyfin_blacklist_error(self, ctx, error):
        print(error)
        await discord_helper.something_went_wrong(ctx=ctx)

    @jellyfin.command(name="status", aliases=['ping', 'up', 'online'], pass_context=True)
    # Anyone can use this command
    async def jellyfin_status(self, ctx: commands.Context):
        """
        Check if the Jellyfin server is online
        """
        jellyfin_api = multi_server_handler.get_jellyfin_api(ctx=ctx)

        if jellyfin_api.ping():
            status_message = f"{jellyfin_api.name} is up and running."
        else:
            status_message = f"{jellyfin_api.name} is having connection issues right now."
        await ctx.send(status_message)

    @jellyfin_status.error
    async def jellyfin_status_error(self, ctx: commands.Context, error):
        print(error)
        await discord_helper.something_went_wrong(ctx=ctx)








    @jellyfin.command(name="winners", pass_context=True)
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def jellyfin_winners(self, ctx: commands.Context):
        """
        List winners' Jellyfin usernames
        """
        try:
            winners = db.get_winners()
            response = '\n'.join([u[0] for u in winners])
            await ctx.send(response)
        except Exception as e:
            await ctx.send("Error pulling winners from database_handler.")

    @jellyfin.command(name="purge", pass_context=True)
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def jellyfin_purge(self, ctx: commands.Context):
        """
        Remove inactive winners
        """
        await ctx.send("Purging winners...")
        await self.purge_winners(ctx)

    @jellyfin.command(name="subcheck")
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def jellyfin_subs(self, ctx: commands.Context):
        """
        Find and removed lapsed subscribers
        This is automatically done once a week
        """
        await self.check_subs()
        await ctx.send("Sub check complete.")

    @jellyfin_subs.error
    async def jellyfin_subs_error(self, ctx, error):
        print(error)
        await ctx.send("Something went wrong.")

    @jellyfin.command(name="trialcheck")
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def jellyfin_trial_check(self, ctx: commands.Context):
        """
        Find and remove lapsed trials
        This is automatically done at the interval set in Settings
        """
        await self.check_trials()
        await ctx.send("Trial check complete.")

    @jellyfin_trial_check.error
    async def jellyfin_trial_check_error(self, ctx, error):
        print(error)
        await ctx.send("Something went wrong.")

    @jellyfin.command(name="cleandb", aliases=['clean', 'scrub', 'syncdb'], pass_context=True)
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def jellyfin_cleandb(self, ctx: commands.Context):
        """
        Remove old users from database_handler
        If you delete a user from Jellyfin directly,
        run this to remove the user's entry in the
        Jellyfin user database_handler.
        """
        existingUsers = get_jellyfin_users()
        dbEntries = db.get_all_entries_in_db()
        if dbEntries:
            deletedUsers = ""
            for entry in dbEntries:
                if entry[1] not in existingUsers.keys():  # entry[1] is JellyfinUsername
                    deletedUsers += entry[1] + ", "
                    db.remove_user_from_db_by_discord(entry[0])  # entry[0] is DiscordID
            if deletedUsers:
                await ctx.send("The following users were deleted from the database_handler: " + deletedUsers[:-2])
            else:
                await ctx.send("No old users found and removed from database_handler.")
        else:
            await ctx.send("An error occurred when grabbing users from the database_handler.")

    @jellyfin_cleandb.error
    async def jellyfin_cleandb_error(self, ctx, error):
        print(error)
        await ctx.send("Something went wrong.")

    @jellyfin.command(name="backupdb")
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def jellyfin_backupdb(self, ctx: commands.Context):
        """
        Backup the database_handler to Dropbox.
        This is automatically done every 24 hours.
        """
        await backup_database()
        await ctx.send("Backup complete.")

    @jellyfin_backupdb.error
    async def jellyfin_backupdb_error(self, ctx, error):
        print(error)
        await ctx.send("Something went wrong.")

    @jellyfin.command(name="count", aliases=["subs", "number"], pass_context=True)
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def jellyfin_count(self, ctx: commands.Context):
        """
        Get the number of enabled Jellyfin users
        """
        count = len(get_jellyfin_users())
        if count > 0:
            await ctx.send(str(settings.JELLYFIN_SERVER_NICKNAME) + " has " + str(count) + " users.")
        else:
            await ctx.send("An error occurred.")

    @jellyfin_count.error
    async def jellyfin_count_error(self, ctx, error):
        print(error)
        await ctx.send("Something went wrong. Please try again later.")

    @jellyfin.command(name="add", aliases=["new", "join"], pass_context=True)
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def jellyfin_add(self, ctx: commands.Context, user: discord.Member, username: str):
        """
        Add a Discord user to Jellyfin
        """
        s, u, p = add_to_jellyfin(username, user.id, 's')
        if s:
            await sendAddMessage(user, username, (p if settings.CREATE_PASSWORD else settings.NO_PASSWORD_MESSAGE))
            await ctx.send(
                "You've been added, {}! Please check your direct messages for login information.".format(user.mention))
        else:
            if "exist" in u:
                await ctx.send(u)
            elif "blacklist" in u:
                await ctx.send("That {} is blacklisted.".format(p))
            else:
                await ctx.send("An error occurred while adding {}".format(user.mention))

    @jellyfin_add.error
    async def jellyfin_add_error(self, ctx, error):
        print(error)
        await ctx.send("Please mention the Discord user to add to Jellyfin, as well as their Jellyfin username.")

    @jellyfin.command(name="remove", aliases=["delete", "rem"], pass_context=True)
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def jellyfin_remove(self, ctx: commands.Context, user: discord.Member):
        """
        Delete a Discord user from Jellyfin
        """
        s = remove_from_jellyfin(user_id=user.id)
        if s == 200:
            await ctx.send("You've been removed from {}, {}.".format(settings.JELLYFIN_SERVER_NICKNAME, user.mention))
        elif s == 600:
            await ctx.send("{} could not be removed.".format(user.mention))
        elif s == 700:
            await ctx.send("There are no accounts for {}".format(user.mention))
        else:
            await ctx.send("An error occurred while removing {}".format(user.mention))

    @jellyfin_remove.error
    async def jellyfin_remove_error(self, ctx, error):
        print(error)
        await ctx.send("Please mention the Discord user to remove from Jellyfin.")

    @jellyfin.command(name="trial", pass_context=True)
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def jellyfin_trial(self, ctx: commands.Context, user: discord.Member, JellyfinUsername: str):
        """
        Start a trial of Jellyfin
        """
        s, u, p = add_to_jellyfin(JellyfinUsername, user.id, 't')
        if s:
            await sendAddMessage(user, JellyfinUsername,
                                 (p if settings.CREATE_PASSWORD else settings.NO_PASSWORD_MESSAGE))
        else:
            if "exist" in u:
                await ctx.send(u)
            elif "blacklist" in u:
                await ctx.send("That {} is blacklisted.".format(p))
            else:
                await ctx.send("An error occurred while starting a trial for {}".format(user.mention))

    @jellyfin_trial.error
    async def jellyfin_trial_error(self, ctx, error):
        print(error)
        await ctx.send("Please mention the Discord user to add to Jellyfin, as well as their Jellyfin username.")

    @jellyfin.command(name='edit', aliases=['update', 'change'])
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def jellyfin_edit(self, ctx: commands.Context, username: Union[discord.Member, str], category: str, *,
                            category_settings: str):
        """
        Update an existing Jellyfin user's restrictions. Can edit library access, sync ability and account status

        Examples:
        - jm edit username share 1 2 4 to limit 'username' to libraries 1, 2 and 4
        - jm edit username sync on to allow 'username' to sync content (offline access)
        - jm edit username livetv off to disable live TV access for 'username'
        - jm edit username account disabled to disable 'username' account (this is different from deletion)
        """
        error_finding_name = False
        jellyfinId = 0
        if isinstance(username, discord.Member):
            results = db.find_user_in_db(ServerOrDiscord="Jellyfin", data=username)
            if not results:
                error_finding_name = True  # user not found
            else:
                jellyfinId = results[0]
        else:
            jellyfinId = jf.getUserIdFromUsername(username=username)
            if not jellyfinId:
                error_finding_name = True  # user not found
        if not error_finding_name:
            category_settings = category_settings.split()
            if category == 'share':
                if 'help' in category_settings:
                    nicks_and_names = jf.get_defined_libraries()
                    await ctx.send("Include the numbers or names of the libraries you want {username} to have access "
                                   "to. Available values (case sensitive): '{nicknames}'".format(username=username,
                                                                                                 nicknames="', '".join(
                                                                                                     nicks_and_names[
                                                                                                         'Nicknames'])
                                                                                                 )
                                   )
                elif category_settings[0].lower() == 'none':
                    new_policy = {'EnableAllFolders': False}
                    if jf.updatePolicy(userId=jellyfinId, policy=new_policy):
                        await ctx.send(f"{username} can no longer access any libraries.")
                    else:
                        await ctx.send(f"Sorry, I couldn't update the library restrictions for {username}.")
                elif category_settings[0].lower() == 'all':
                    new_policy = {'EnableAllFolders': True}
                    if jf.updatePolicy(userId=jellyfinId, policy=new_policy):
                        await ctx.send(f"{username} can now access all libraries.")
                    else:
                        await ctx.send(f"Sorry, I couldn't update the library restrictions for {username}.")
                else:
                    # convert '4kmovie' -> 'Movies (4K)'
                    nicks_and_names = jf.get_defined_libraries()
                    translated_library_names = []
                    for i in range(0, len(nicks_and_names['Nicknames'])):
                        if nicks_and_names['Nicknames'][i] in category_settings:
                            translated_library_names.append(nicks_and_names['Full Names'][i])
                    # convert 'Movies (4K)' -> library ID
                    all_libraries = jf.getAllLibraries()
                    libraries_to_add = []
                    for lib in all_libraries['Items']:
                        if lib['Name'] in translated_library_names:
                            libraries_to_add.append(lib['Id'])
                    # try again, looking in library names rather than user-defined ones in settings
                    for lib in all_libraries['Items']:
                        if lib['Name'] in category_settings and lib['Id'] not in libraries_to_add:
                            libraries_to_add.append(lib['Id'])
                    if libraries_to_add and len(libraries_to_add) == len(category_settings):
                        new_policy = {"EnabledFolders": libraries_to_add, 'EnableAllFolders': False}
                        if jf.updatePolicy(userId=jellyfinId, policy=new_policy):
                            await ctx.send(f"{username} can now only access those {len(libraries_to_add)} libraries.")
                        else:
                            await ctx.send(f"Sorry, I couldn't update the library restrictions for {username}.")
                    else:
                        await ctx.send("Sorry, I couldn't find one or more of those libraries.")
            elif category == 'livetv':
                if category_settings[0].lower() in ['yes', 'true', 'on', 'enable']:
                    new_policy = {'EnableLiveTvAccess': True}
                    if jf.updatePolicy(userId=jellyfinId, policy=new_policy):
                        await ctx.send(f"Live TV access is now enabled for {username}.")
                    else:
                        await ctx.send(f"Could not enable live TV access for {username}.")
                elif category_settings[0].lower() in ['no', 'false', 'off', 'disable']:
                    new_policy = {'EnableLiveTvAccess': False}
                    if jf.updatePolicy(userId=jellyfinId, policy=new_policy):
                        await ctx.send(f"Live TV access is now disabled for {username}.")
                    else:
                        await ctx.send(f"Could not disable live TV access for {username}.")
                else:
                    await ctx.send("Please indicate 'on' or 'off' for live TV setting.")
            elif category in ['sync', 'download']:
                if category_settings[0].lower() in ['yes', 'true', 'on', 'enable']:
                    new_policy = {'EnableContentDownloading': True}
                    if jf.updatePolicy(userId=jellyfinId, policy=new_policy):
                        await ctx.send(f"Sync is now enabled for {username}.")
                    else:
                        await ctx.send(f"Could not enable sync for {username}.")
                elif category_settings[0].lower() in ['no', 'false', 'off', 'disable']:
                    new_policy = {'EnableContentDownloading': False}
                    if jf.updatePolicy(userId=jellyfinId, policy=new_policy):
                        await ctx.send(f"Sync is now disabled for {username}.")
                    else:
                        await ctx.send(f"Could not disable sync for {username}.")
                else:
                    await ctx.send("Please indicate 'on' or 'off' for sync setting.")
            elif category == 'account':
                if category_settings[0].lower() in ['enabled', 'on', 'enable']:
                    if jf.disableUser(userId=jellyfinId, enable=True):
                        await ctx.send(f"{username} is now enabled.")
                    else:
                        await ctx.send(f"Could not enable account for {username}.")
                elif category_settings[0].lower() in ['disabled', 'off', 'disable']:
                    if jf.disableUser(userId=jellyfinId, enable=False):
                        await ctx.send(f"{username} is now disabled.")
                    else:
                        await ctx.send(f"Could not disable account for {username}.")
                else:
                    await ctx.send("Please indicate 'on' or 'off' for account enabled setting.")
            else:
                await ctx.send(
                    "That's not a valid option. Please indicate 'share', 'sync', 'livetv' or 'account'. See help for more details.")
        else:
            await ctx.send(
                "Could not find that Discord user's Jellyfin username. Try again with their Jellyfin username instead.")

    @jellyfin_edit.error
    async def jellyfin_edit_error(self, ctx, error):
        print(error)
        await ctx.send("Sorry, something went wrong.")

    @jellyfin.command(name='details', aliases=['restrictions'], pass_context=True)
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def jellyfin_details(self, ctx: commands.Context, username: Union[discord.Member, str]):
        error_finding_name = False
        jellyfinId = 0
        if isinstance(username, discord.Member):
            results = db.find_user_in_db(ServerOrDiscord="Jellyfin", data=username)
            if not results:
                error_finding_name = True  # user not found
            else:
                jellyfinId = results[0]
        else:
            jellyfinId = jf.getUserIdFromUsername(username=username)
            if not jellyfinId:
                error_finding_name = True  # user not found
        if not error_finding_name:
            details = jf.getUserDetailsSimplified(user_id=jellyfinId)
            if details:
                embed = discord.Embed(title=f"Jellyfin settings for {details['Name']}")
                if details.get('Admin') is not None:
                    embed.add_field(name='Administrator', value=('Yes' if details['Admin'] else 'No'), inline=False)
                if details.get('Disabled') is not None:
                    embed.add_field(name='Enabled', value=('Yes' if not details['Disabled'] else 'No'), inline=False)
                if details.get('EnabledFolderNames') is not None:
                    embed.add_field(name='Shared Sections', value=(
                        ", ".join(details['EnabledFolderNames']) if details['EnabledFolderNames'] else 'None'),
                                    inline=False)
                if details.get('DownloadContent') is not None:
                    embed.add_field(name='Can Download', value=('Yes' if details['DownloadContent'] else 'No'),
                                    inline=False)
                if details.get('LiveTVAccess') is not None:
                    embed.add_field(name='Can Watch Live TV', value=('Yes' if details['LiveTVAccess'] else 'No'),
                                    inline=False)
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"Sorry, I couldn't find the settings for {username}.")
        else:
            await ctx.send(
                "Could not find that Discord user's Jellyfin username. Try again with their Jellyfin username instead.")

    @jellyfin_details.error
    async def jellyfin_details_error(self, ctx, error):
        print(error)
        await ctx.send("Sorry, something went wrong.")

    @jellyfin.command(name="import", pass_context=True)
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def jellyfin_import(self, ctx: commands.Context, user: discord.Member, JellyfinUsername: str, subType: str,
                              serverNumber: int = None):
        """
        Add existing Jellyfin users to the database_handler.
        user - tag a Discord user
        JellyfinUsername - Jellyfin username of the Discord user
        subType - custom note for tracking subscriber type; MUST be less than 5 letters.
        Default in database_handler: 's' for Subscriber, 'w' for Winner, 't' for Trial.
        NOTE: subType 't' will make a new 24-hour timestamp for the user.
        """
        users = get_jellyfin_users()
        if JellyfinUsername not in users.keys():
            await ctx.send("Not an existing Jellyfin user.")
        else:
            jellyfinId = users[JellyfinUsername]
            if len(subType) > 4:
                await ctx.send("subType must be less than 5 characters long.")
            else:
                new_entry = db.add_user_to_db(discord_id=user.id, username=JellyfinUsername, note=subType,
                                              uid=jellyfinId)
                if new_entry:
                    if subType == 't':
                        await ctx.send("Trial user was added/new timestamp issued.")
                    else:
                        await ctx.send("User added to the database_handler.")
                else:
                    await ctx.send("User already exists in the database_handler.")

    @jellyfin_import.error
    async def jellyfin_import_error(self, ctx, error):
        print(error)
        await ctx.send(
            "Please mention the Discord user to add to the database_handler, including their Jellyfin username and sub type.")

    @jellyfin.group(name="find", aliases=["id"], pass_context=True)
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def jellyfin_find(self, ctx: commands.Context):
        """
        Find Discord or Jellyfin user
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")

    @jellyfin_find.command(name="jellyfin", aliases=["j"])
    async def jellyfin_find_jellyfin(self, ctx: commands.Context, user: discord.Member):
        """
        Find Discord member's Jellyfin username
        """
        name, note = db.find_username_in_db(ServerOrDiscord="Jellyfin", data=user.id)
        if name:
            await ctx.send('{} is Jellyfin user: {}{}'.format(user.mention, name,
                                                              (" [Trial]" if note == 't' else " [Subscriber]")))
        else:
            await ctx.send("User not found.")

    @jellyfin_find.command(name="discord", aliases=["d"])
    async def jellyfin_find_discord(self, ctx: commands.Context, JellyfinUsername: str):
        """
        Find Jellyfin user's Discord name
        """
        id, note = db.find_username_in_db(ServerOrDiscord="Discord", data=JellyfinUsername)
        if id:
            await ctx.send('{} is Discord user: {}'.format(JellyfinUsername, self.bot.get_user(int(id)).mention))
        else:
            await ctx.send("User not found.")

    @jellyfin_find.error
    async def jellyfin_find_error(self, ctx, error):
        await ctx.send("An error occurred while looking for that user.")
        print(error)

    @jellyfin.group(name="info")
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def jellyfin_info(self, ctx: commands.Context):
        """
        Get database_handler entry for a user
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")

    @jellyfin_info.command(name="jellyfin", aliases=["j"])
    async def jellyfin_info_jellyfin(self, ctx, JellyfinUsername: str):
        """
        Get database_handler entry for Jellyfin username
        """
        embed = discord.Embed(title=("Info for {}".format(str(JellyfinUsername))))
        n = db.describe_table(file=settings.SQLITE_FILE, table="users")
        d = db.find_entry_in_db(fieldType="JellyfinUsername", data=JellyfinUsername)
        if d:
            for i in range(0, len(n)):
                val = str(d[i])
                if str(n[i][1]) == "DiscordID":
                    val = val + " (" + self.bot.get_user(int(d[i])).mention + ")"
                if str(n[i][1]) == "Note":
                    val = ("Trial" if d[i] == 't' else "Subscriber")
                if d[i] is not None:
                    embed.add_field(name=str(n[i][1]), value=val, inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send("That user is not in the database_handler.")

    @jellyfin_info.command(name="discord", aliases=["d"])
    async def jellyfin_info_discord(self, ctx, user: discord.Member):
        """
        Get database_handler entry for Discord user
        """
        embed = discord.Embed(title=("Info for {}".format(user.name)))
        n = db.describe_table(file=settings.SQLITE_FILE, table="users")
        d = db.find_entry_in_db(fieldType="DiscordID", data=user.id)
        if d:
            for i in range(0, len(n)):
                name = str(n[i][1])
                val = str(d[i])
                if str(n[i][1]) == "DiscordID":
                    val = val + " (" + self.bot.get_user(int(d[i])).mention + ")"
                if str(n[i][1]) == "Note":
                    val = ("Trial" if d[i] == 't' else "Subscriber")
                if d[i] is not None:
                    embed.add_field(name=str(n[i][1]), value=val, inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send("That user is not in the database_handler.")

    @jellyfin_info.error
    async def jellyfin_info_error(self, ctx, error):
        print(error)
        await ctx.send("User not found.")

    @jellyfin.command(name="migrate", pass_context=True)
    async def jellyfin_migrate(self, ctx: commands.Context):
        """
        Migrate Plex users to Jellyfin (using a CSV file)
        File format: Discord_Tag | Plex_Username | Jellyfin_Username
        """
        users = {}
        count = 0
        failed = []
        with open(settings.MIGRATION_FILE + '.csv', mode='r') as f:
            reader = csv.DictReader(f)
            writer = csv.writer(f)
            for row in reader:
                jellyfin_username = row['Discord_Tag'].split("#")[0]  # Jellyfin username will be Discord username
                user = discord.utils.get(ctx.message.guild.members, name=jellyfin_username)
                s, u, p = add_to_jellyfin(jellyfin_username, user.id, 's')  # Users added as 'Subscribers'
                if s:
                    await sendAddMessage(user, jellyfin_username,
                                         (p if settings.CREATE_PASSWORD else settings.NO_PASSWORD_MESSAGE))
                    data = [str(row['Discord_Tag']), str(row['Plex_Username']), str(jellyfin_username)]
                    writer.writerow(data)
                    count += 1
                else:
                    failed.append(jellyfin_username)
            f.close()
        await ctx.send("{} users added to Jellyfin.{}".format(str(count), (
            "" if len(failed) == 0 else "The following users were not added successfully: " + "\n".join(failed))))

    @commands.Cog.listener()
    async def on_message(self, message):
        if settings.AUTO_WINNERS:
            if message.author.id == settings.GIVEAWAY_BOT_ID and "congratulations" in message.content.lower() and message.mentions:
                tempWinner = discord.utils.get(message.guild.roles, name=settings.TEMP_WINNER_ROLE_NAME)
                for u in message.mentions:
                    await u.add_roles(tempWinner, reason="Winner - access winner invite channel")
            if message.channel.id == settings.WINNER_CHANNEL and discord.utils.get(message.guild.roles,
                                                                                   name=settings.TEMP_WINNER_ROLE_NAME) in message.author.roles:
                username = message.content.strip()  # Only include username, nothing else
                s, u, p = add_to_jellyfin(username, message.author.id, 'w')
                if s:
                    await sendAddMessage(message.author, username,
                                         (p if settings.CREATE_PASSWORD else settings.NO_PASSWORD_MESSAGE))
                    await message.channel.send(
                        "You've been added, {}! Please check your direct messages for login information.".format(
                            message.author.mention))
                    await message.author.remove_roles(
                        discord.utils.get(message.guild.roles, name=settings.TEMP_WINNER_ROLE_NAME),
                        reason="Winner was processed successfully.")
                else:
                    if "exist" in u:
                        await message.channel.send(u)
                    elif "blacklist" in u:
                        await message.channel.send("That {} is blacklisted.".format(p))
                    else:
                        await message.channel.send("An error occurred while adding {}".format(message.author.mention))

    @commands.Cog.listener()
    async def on_ready(self):
        """
        self.check_trials_timer.start()
        self.check_subs_timer.start()
        """
        pass


def setup(bot):
    bot.add_cog(JellyfinManager(bot))
