"""
Interact with a Plex Media Server, manage users
Copyright (C) 2020 Nathan Harris
"""

# TODO: Readd the HAS_ROLE decorators
import time
from typing import Union, List
import asyncio

import discord
from discord.ext import commands

import helper.discord_helper as discord_helper
import helper.utils as utils
from media_server.media_server_cog import MediaServerCog
from database.media_servers.media_server_database import PlexUser
from media_server.plex import settings as plex_settings
from media_server.plex import plex_api as px_api


class PlexManager(MediaServerCog):
    def __init__(self, bot):
        super().__init__(bot)

    # TODO Start here with new Tautulli library
    async def check_winners(self, ctx: commands.Context):
        api = self.get_api(ctx=ctx)

        try:
            number_removed = 0
            winners_usernames = [winner.MediaServerUsername for winner in api.database.winners]

            for server in api.all_plex_instances:
                tautulli_users = server.tautulli.users
                for tautulli_user in tautulli_users:
                    if tautulli_user.username in winners_usernames:
                        if server.tautulli.get_last_time_user_seen(
                                user_id=tautulli_user.username) < utils.timestamp_x_days_from_now(
                                -14):  # user not seen in 14 days
                            if self.remove_from_plex_remove_from_database_remove_role_send_dm(ctx=ctx,
                                                                                         plex_username=tautulli_user.username,
                                                                                         role_name=plex_settings.WINNER_ROLE_NAME,
                                                                                         role_reason="Inactive winner",
                                                                                         dm_message=f"You have been removed from {server.name} due to inactivity."):
                                number_removed += 1
                        else:
                            user_stats = server.tautulli.get_user_watch_time_stats(user_id=tautulli_user.username,
                                                                                   days=7)  # check last 14 days
                            if not user_stats:
                                raise Exception(f"Could not get watch stats for winner {tautulli_user.username}")
                                # continue
                            user_stats = user_stats.stats[0]
                            if user_stats.total_time < plex_settings.WINNER_THRESHOLD:
                                if self.remove_from_plex_remove_from_database_remove_role_send_dm(ctx=ctx,
                                                                                             plex_username=tautulli_user.username,
                                                                                             role_name=plex_settings.WINNER_ROLE_NAME,
                                                                                             role_reason="Inactive winner",
                                                                                             dm_message=f"You have been removed from {server.name} due to inactivity."):
                                    number_removed += 1

            await self.respond(f"{number_removed} inactive winner(s) purged.", ctx=ctx)
        except Exception as e:
            print(e)
            await discord_helper.something_went_wrong(ctx=ctx)

    def get_user_entries_from_database(self,
                                       ctx: commands.Context, discord_id: int = None, plex_username: str = None,
                                       first_only: bool = False) -> Union[
        List[Union[PlexUser, utils.StatusResponse]], utils.StatusResponse]:
        if not discord_id and not plex_username:
            raise Exception("Must provide either plex_username or discord_id")

        api = self.get_api(ctx=ctx)

        database_user_entries = api.database.get_user(discord_id=discord_id, media_server_username=plex_username,
                                                      first_match_only=first_only)
        if not database_user_entries:
            return utils.StatusResponse(success=False, issue="User not found in database")
        return database_user_entries

    def remove_user_from_database(self,
                                  ctx: commands.Context, user=None, discord_id: int = None,
                                  plex_username: str = None) -> utils.StatusResponse:
        if not user and not discord_id and not plex_username:
            raise Exception("Must provide either user, plex_username or discord_id")

        api = self.get_api(ctx=ctx)

        if not user:
            user = api.database.make_user(discord_id=discord_id, plex_username=plex_username)
        if not api.database.remove_user_from_database(user=user):
            return utils.StatusResponse(success=False, issue="Could not remove user from database.")
        return utils.StatusResponse(success=True)

    async def add_user_to_single_plex_et_al(self,
                                            ctx: commands.Context,
                                            plex_username: str,
                                            user_type: str,
                                            server_number: int = None) -> utils.StatusResponse:
        """
        Add a user to a single Plex instance ( + Ombi/Tautulli)

        :param user_type:
        :type user_type:
        :param ctx:
        :type ctx:
        :param plex_username:
        :type plex_username:
        :param server_number:
        :type server_number:
        :return:
        :rtype:
        """
        api = self.get_api(ctx=ctx)

        try:
            plex_server = api.get_plex_instance(server_number=server_number)
            response = plex_server.add_user(plex_username=plex_username)
            if not response:
                return response
            await asyncio.sleep(30)
            plex_server.refresh_tautulli_users()
            if user_type != 'Trial':  # Trial members do not have access to Ombi
                plex_server.refresh_ombi_users()
            return utils.StatusResponse(success=True)
        except Exception as e:
            print(e)
            return utils.StatusResponse(success=False, issue=e.__str__())

    async def _remove_user_from_single_plex_et_al(self,
                                                  ctx: commands.Context,
                                                  plex_username: str,
                                                  server_nummber: int = None) -> utils.StatusResponse:
        """
        Remove a user from a single Plex instance ( + Ombi/Tautulli)

        :param ctx:
        :type ctx:
        :param plex_username:
        :type plex_username:
        :param server_nummber:
        :type server_nummber:
        :return:
        :rtype:
        """
        api = self.get_api(ctx=ctx)

        try:
            plex_server = api.get_plex_instance(server_number=server_nummber)
            response = plex_server.remove_user(plex_username=plex_username)
            if not response:
                return response
            plex_server.delete_user_from_tautulli(plex_username=plex_username)
            plex_server.delete_user_from_ombi(username=plex_username)
            return utils.StatusResponse(success=True)
        except Exception as e:
            return utils.StatusResponse(success=False, issue=e.__str__())

    async def remove_user_from_plex_et_al(self,
                                          ctx: commands.Context,
                                          plex_username: str,
                                          plex_servers_numbers: List[int] = [None]) -> utils.StatusResponse:
        """
        Remove a user from one or all Plex server(s) ( + Ombi/Tautulli)
        """
        for server_number in plex_servers_numbers:
            status = await self._remove_user_from_single_plex_et_al(ctx=ctx, plex_username=plex_username,
                                                               server_nummber=server_number)
            if not status:
                return status
        return utils.StatusResponse(success=True)

    def get_server_numbers_user_is_on(self,
                                      ctx: commands.Context,
                                      plex_username: str = None,
                                      discord_id: int = None) -> Union[utils.StatusResponse, List[int]]:
        """
        Get a list of the Plex server numbers that the user is on

        :param ctx:
        :type ctx:
        :param plex_username:
        :type plex_username:
        :param discord_id:
        :type discord_id:
        :return:
        :rtype:
        """
        database_user_entries = self.get_user_entries_from_database(ctx=ctx, discord_id=discord_id,
                                                               plex_username=plex_username,
                                                               first_only=False)
        if not database_user_entries:
            return database_user_entries  # error message

        return [entry.WhichPlexServer for entry in database_user_entries]

    async def remove_from_plex_remove_from_database_remove_role_send_dm(self,
                                                                        ctx: commands.Context,
                                                                        role_name: str,
                                                                        role_reason: str,
                                                                        dm_message: str,
                                                                        plex_username: str = None,
                                                                        discord_id: int = None):
        database_user_entries = self.get_user_entries_from_database(ctx=ctx, discord_id=discord_id,
                                                               plex_username=plex_username)
        if not database_user_entries:
            return database_user_entries  # error message

        response = await self.remove_user_from_plex_et_al(ctx=ctx, plex_username=plex_username)
        if not response:
            return response

        for entry in database_user_entries:
            # delete all entries in database
            response = self.remove_user_from_database(ctx=ctx, user=entry)
            if not response:
                return response

        discord_user = await discord_helper.get_user(user_id=database_user_entries[0].DiscordID, ctx=ctx)
        if not discord_user:
            return utils.StatusResponse(success=False, issue="Could not load Discord user to modify roles.")

        if not await discord_helper.remove_user_role(user=discord_user, role_name=role_name, reason=role_reason):
            return utils.StatusResponse(success=False, issue=f"Could not remove {role_name} role from Discord user.")

        await discord_helper.send_direct_message(user=discord_user, message=dm_message)

        return utils.StatusResponse(success=True)

    async def check_trials(self,
                           ctx: commands.Context,
                           api=None):
        for trial_database_user in api.database.expired_trials:
            await self.remove_from_plex_remove_from_database_remove_role_send_dm(ctx=ctx,
                                                                            role_name=plex_settings.TRIAL_ROLE_NAME,
                                                                            role_reason="Trial ended.",
                                                                            dm_message="Your trial has ended.",
                                                                            plex_username=trial_database_user.MediaServerUsername,
                                                                            discord_id=trial_database_user.DiscordID)

    async def add_to_database_add_to_plex_add_role_send_dm(self, 
                                                           ctx: commands.Context,
                                                           plex_username: str,
                                                           discord_id: int,
                                                           user_type: str,
                                                           role_name: str,
                                                           role_reason: str,
                                                           dm_message: str,
                                                           plex_server_number: int = None,
                                                           pay_method: str = None):
        if self.check_blacklist(ctx=ctx, discord_id=discord_id, username=plex_username):
            return utils.StatusResponse(success=False, issue="USER ON BLACKLIST", code=999)

        api = self.get_api(ctx=ctx)

        expiration_stamp = None
        if user_type == 'Trial':
            expiration_stamp = int(time.time()) + plex_settings.TRIAL_LENGTH
        new_database_entry = api.database.make_user(plex_username=plex_username,
                                                    discord_id=discord_id,
                                                    user_type=user_type,
                                                    pay_method=pay_method,
                                                    which_plex_server=(
                                                        plex_server_number if plex_server_number else None),
                                                    expiration_stamp=expiration_stamp)

        response = api.database.add_user_to_database(new_database_entry)
        if not response:
            return response

        response = await self.add_user_to_single_plex_et_al(ctx=ctx, plex_username=plex_username, user_type=user_type,
                                                       server_number=plex_server_number)
        if not response:
            return response

        discord_user = await discord_helper.get_user(user_id=discord_id, ctx=ctx)
        if not discord_user:
            return utils.StatusResponse(success=False, issue="Could not load Discord user to modify roles.")

        if not await discord_helper.add_user_role(user=discord_user, role_name=role_name, reason=role_reason):
            return utils.StatusResponse(success=False, issue=f"Could not add {role_name} role to Discord user.")

        await discord_helper.send_direct_message(user=discord_user, message=dm_message)

        return utils.StatusResponse(success=True)

    async def add_to_database_add_role(self, 
                                       ctx: commands.Context,
                                       plex_username: str,
                                       discord_id: int,
                                       user_type: str,
                                       role_name: str,
                                       role_reason: str,
                                       plex_server_number: int = None,
                                       pay_method: str = None):
        if self.check_blacklist(ctx=ctx, discord_id=discord_id, username=plex_username):
            return utils.StatusResponse(success=False, status_code=utils.StatusCodes.USER_ON_BLACKLIST)

        api = self.get_api(ctx=ctx)

        servers_with_access = []
        for plex_server in api.all_plex_instances:
            if plex_server.user_has_access(plex_username=plex_username):
                servers_with_access.append(plex_server.name)
        if not servers_with_access:
            return utils.StatusResponse(success=False, status_code=utils.StatusCodes.USER_NOT_ON_PLEX)

        new_database_entry = api.database.make_user(plex_username=plex_username,
                                                    discord_id=discord_id,
                                                    user_type=user_type,
                                                    pay_method=pay_method,
                                                    which_plex_server=(
                                                        plex_server_number if plex_server_number else None))

        response = api.database.add_user_to_database(new_database_entry)
        if not response:
            return response

        discord_user = await discord_helper.get_user(user_id=discord_id, ctx=ctx)
        if not discord_user:
            return utils.StatusResponse(success=False, issue="Could not load Discord user to modify roles.")

        if not await discord_helper.add_user_role(user=discord_user, role_name=role_name, reason=role_reason):
            return utils.StatusResponse(success=False, issue=f"Could not add {role_name} role to Discord user.")

        return utils.StatusResponse(success=True)

    async def check_subs(self, ctx: commands.Context):
        for discord_member in discord_helper.get_users_without_roles(bot=self.bot,
                                                                     role_names=plex_settings.SUB_ROLES,
                                                                     guild=ctx.message.guild):
            if discord_member.id not in plex_settings.EXEMPT_SUBS:
                await self.remove_from_plex_remove_from_database_remove_role_send_dm(ctx=ctx,
                                                                                discord_id=discord_member.id,
                                                                                role_name=plex_settings.INVITED_ROLE,
                                                                                role_reason="Subscription ended.",
                                                                                dm_message=f"You have been removed from Plex because your subscription has ended.")

    """
    @tasks.loop(hours=24)
    async def backup_database_timer(self):
        await backup_database()
    """

    """
    @tasks.loop(hours=plex_settings.SUB_CHECK_TIME * 24)
    async def check_subs_timer(self):
        await self.check_subs()

    @tasks.loop(minutes=plex_settings.TRIAL_CHECK_FREQUENCY)
    async def check_trials_timer(self):
        await check_trials()

    @tasks.loop(seconds=60)
    async def check_playing(self):
        activity = px.t_request('get_activity')
        if activity:
            guild = await self.bot.fetch_guild(settings.DISCORD_SERVER_ID)
            if guild:
                watching_role = discord.utils.get(guild.roles,
                                                  name=settings.CURRENTLY_PLAYING_ROLE_NAME)
                guild = self.bot.get_guild(guild.id)  # Yes, this is unfortunately necessary
                users_with_role = [member for member in guild.members if (watching_role in member.roles)]
                active_users = [session['username'] for session in activity['response']['data']['sessions']]
                # print('Users currently using Plex: {}'.format(active_users))
                # Remove old users first
                for user in users_with_role:
                    plexUsername = db.find_user_in_db(ServerOrDiscord='Plex', data=str(user.id))[0]
                    if not plexUsername or plexUsername not in active_users:
                        await user.remove_roles(watching_role, reason="Not watching Plex.")
                # Now add new users
                for username in active_users:
                    discordID = db.find_user_in_db(ServerOrDiscord='Discord', data=username)
                    if discordID:
                        await guild.add_roles(watching_role, reason="Is watching Plex.")
                        
    """
    @commands.group(name="pm", aliases=["PM", "PlexMan", "plexman", "PlexManager", "plexmanager"], pass_context=True)
    async def pm(self, ctx: commands.Context):
        """
        Plex admin commands
        """
        await self.what_subcommand(ctx=ctx)

    @pm.command(name="access", pass_context=True)
    # Anyone can use this command
    async def pm_access(self, ctx: commands.Context, plex_username: str = None):
        """
        Check if you or another user has access to the Plex server
        Currently does not support multiple Plex servers
        """
        _plex_username = plex_username

        if not _plex_username:
            database_user = self.get_user_entries_from_database(ctx=ctx, discord_id=ctx.message.author.id, first_only=True)
            if not database_user:
                message = "Could not find your Plex username in the database."
            else:
                _plex_username = database_user[0].MediaServerUsername

        api = self.get_api(ctx=ctx)

        if _plex_username:
            servers_with_access = []
            for plex_server in api.all_plex_instances:
                if plex_server.user_has_access(plex_username=_plex_username):
                    servers_with_access.append(plex_server.name)

            if servers_with_access:
                message = (
                              "You have " if not plex_username else f"{_plex_username} has ") + f"access to {len(servers_with_access)} Plex server(s)."
            else:
                message = (
                              "You do not have " if not plex_username else f"{_plex_username} does not have ") + "access to any of the Plex servers."
        await self.respond(message, ctx=ctx)

    @pm_access.error
    async def pm_access_error(self, ctx: commands.Context, error):
        print(error)
        await discord_helper.something_went_wrong(ctx=ctx)

    @pm.command(name="status", aliases=['ping', 'up', 'online'], pass_context=True)
    # Anyone can use this command
    async def pm_status(self, ctx: commands.Context):
        """
        Check if the Plex server(s) is/are online
        """
        api = self.get_api(ctx=ctx)

        status_messages = []
        for plex_server in api.all_plex_instances:
            if plex_server.ping():
                status_messages.append(f"{plex_server.name} is up and running.")
            else:
                status_messages.append(f"{plex_server.name} is having connection issues right now.")
        message = '\n'.join(status_messages)
        await self.respond(message, ctx=ctx)

    @pm_status.error
    async def pm_status_error(self, ctx: commands.Context, error):
        print(error)
        await discord_helper.something_went_wrong(ctx=ctx)

    @pm.command(name="trials", pass_context=True)
    async def pm_trials(self, ctx: commands.Context):
        """
        List trials' Plex usernames
        """
        api = self.get_api(ctx=ctx)

        trials = api.database.trials
        if trials:
            await self.respond("Trials:\n" + "\n".join(trial.MediaServerUsername for trial in trials), ctx=ctx)
        else:
            await self.respond("No current trials.", ctx=ctx)

    @pm_trials.error
    async def pm_trials_error(self, ctx: commands.Context, error):
        print(error)
        await self.respond("Error pulling trial users from the database.", ctx=ctx)

    @pm.command(name="winners", pass_context=True)

    async def pm_winners(self, ctx: commands.Context):
        """
        List winners' Plex usernames
        """
        api = self.get_api(ctx=ctx)

        winners = api.database.winners
        if winners:
            await self.respond("Winners:\n" + "\n".join(winner.MediaServerUsername for winner in winners), ctx=ctx)
        else:
            await self.respond("No current winners.", ctx=ctx)

    @pm_winners.error
    async def pm_winners_error(self, ctx: commands.Context, error):
        print(error)
        await self.respond("Error pulling winners from the database.", ctx=ctx)

    @pm.command(name="users", pass_context=True)

    async def pm_users(self, ctx: commands.Context):
        """
        List users' Plex usernames
        """
        api = self.get_api(ctx=ctx)

        users = api.database.users
        if users:
            await self.respond("Users:\n" + "\n".join(user.MediaServerUsername for user in users), ctx=ctx)
        else:
            await self.respond("No current users.", ctx=ctx)

    @pm_users.error
    async def pm_users_error(self, ctx: commands.Context, error):
        print(error)
        await self.respond("Error pulling users from the database.", ctx=ctx)

    @pm.command(name="purge", pass_context=True)

    async def pm_purge(self, ctx: commands.Context):
        """
        Remove inactive winners
        """
        await self.respond("Purging winners...", ctx=ctx)
        await self.check_winners(ctx=ctx)

    @pm_purge.error
    async def pm_purge_error(self, ctx: commands.Context, error):
        print(error)
        await discord_helper.something_went_wrong(ctx=ctx)

    @pm.command(name="subcheck")

    async def pm_subs(self, ctx: commands.Context):
        """
        Find and removed lapsed subscribers
        """
        await self.check_subs(ctx=ctx)
        await self.respond("Subscriber check complete.", ctx=ctx)

    @pm_subs.error
    async def pm_subs_error(self, ctx: commands.Context, error):
        print(error)
        await discord_helper.something_went_wrong(ctx=ctx)

    @pm.command(name="trialcheck")

    async def pm_trial_check(self, ctx: commands.Context):
        """
        Find and remove lapsed trials
        """
        await self.check_trials(ctx=ctx)
        await self.respond("Trial check complete.", ctx=ctx)

    @pm_trial_check.error
    async def pm_trial_check_error(self, ctx, error):
        print(error)
        await discord_helper.something_went_wrong(ctx=ctx)

    @pm.command(name="cleandb", aliases=["clean", "scrub", "syncdb"], pass_context=True)

    async def pm_cleandb(self, ctx: commands.Context):
        """
        Remove old users from database_handler
        If you delete a user from Plex directly,
        run this to remove the user's entry in the
        Plex database.
        """
        api = self.get_api(ctx=ctx)

        existing_users = []
        for plex_server in api.all_plex_instances:
            existing_users.extend([user.username.lower() for user in plex_server.plex_friends])

        database_users = api.database.users
        if database_users:
            usernames_to_delete = []
            for database_user in database_users:
                if database_user.MediaServerUsername.lower() not in existing_users:
                    usernames_to_delete.append(database_user.MediaServerUsername)
                    self.remove_user_from_database(ctx=ctx, user=database_user)
            if usernames_to_delete:
                message = "The following users were deleted from your database:\n" + "\n".join(usernames_to_delete)
            else:
                message = "No dangling users were found."
            await self.respond(message, ctx=ctx)
        else:
            await self.respond("An error occurred when grabbing data from the database.", ctx=ctx)

    @pm_cleandb.error
    async def pm_cleandb_error(self, ctx: commands.Context, error):
        print(error)
        await discord_helper.something_went_wrong(ctx=ctx)

    """
    @pm.command(name="backupdb")
    
    async def pm_backupdb(self, ctx: commands.Context):
        await backup_database()
        await self.respond("Backup complete.", ctx=ctx)

    @pm_backupdb.error
    async def pm_backupdb_error(self, ctx, error):
        print(error)
        await self.respond("Something went wrong.", ctx=ctx)
    """

    @pm.command(name="count")

    async def pm_count(self, ctx: commands.Context):
        """
        Check Plex share count
        """
        api = self.get_api(ctx=ctx)

        count_messages = []
        for plex_server in api.all_plex_instances:
            count_messages.append(f"{plex_server.name} has {len(plex_server.users)} users.")
        message = "\n".join(count_messages)
        await self.respond(message, ctx=ctx)

    @pm_count.error
    async def pm_count_error(self, ctx: commands.Context, error):
        print(error)
        await discord_helper.something_went_wrong(ctx=ctx)

    @pm.command(name="add", aliases=["invite", "new"], pass_context=True)

    async def pm_add(self, ctx: commands.Context, user: discord.Member, plex_username: str, server_number: int = None):
        """
        Add a Discord user to Plex
        Mention the Discord user and their Plex username
        Include optional serverNumber to add to a specific server (if using multiple Plex servers)
        """
        await self.respond(f"Adding {plex_username} to Plex {f' (Server {server_number})' if server_number else ''}", ctx=ctx)
        response = await self.add_to_database_add_to_plex_add_role_send_dm(ctx=ctx,
                                                                      plex_username=plex_username,
                                                                      discord_id=user.id,
                                                                      user_type='Subscriber',
                                                                      role_name=plex_settings.INVITED_ROLE,
                                                                      role_reason='Subscription started',
                                                                      dm_message="You've been invited! Check your Plex invites to accept.",
                                                                      plex_server_number=server_number)
        if not response:
            await self.respond(response.issue, ctx=ctx)
        else:
            await self.respond(f"{discord_helper.mention_user(user_id=user.id)}. You've been invited, {plex_username}!", ctx=ctx)

    @pm_add.error
    async def pm_add_error(self, ctx, error):
        print(error)
        await self.respond("Please mention the Discord user to add to Plex, as well as their Plex username.", ctx=ctx)

    @pm.command(name="remove", aliases=["uninvite", "delete", "rem"])

    async def pm_remove(self, ctx: commands.Context, user: discord.Member):
        """
        Remove a Discord user from Plex
        """
        response = await self.remove_from_plex_remove_from_database_remove_role_send_dm(ctx=ctx,
                                                                                   discord_id=user.id,
                                                                                   role_name=plex_settings.INVITED_ROLE,
                                                                                   role_reason="Subscription ended",
                                                                                   dm_message="You have been removed from Plex.")

        if not response:
            await self.respond(response.issue, ctx=ctx)
        else:
            await self.respond(f"{discord_helper.mention_user(user_id=user.id)}, you have been removed from Plex.", ctx=ctx)

    @pm_remove.error
    async def pm_remove_error(self, ctx, error):
        print(error)
        await self.respond("Please mention the Discord user to remove from Plex.", ctx=ctx)

    @pm.command(name="import")

    async def pm_import(self, ctx: commands.Context, user: discord.Member, plex_username: str,
                        server_number: int = None):
        """
        Import an existing Plex-Discord user to the database (does not support Trials or Winners)
        Mention the Discord user and their Plex username
        Include optional server number (if using multiple Plex servers)
        """
        await self.respond(f"Importing {plex_username} to database...", ctx=ctx)
        response = await self.add_to_database_add_role(ctx=ctx,
                                                  plex_username=plex_username,
                                                  discord_id=user.id,
                                                  user_type='Subscriber',
                                                  role_name=plex_settings.INVITED_ROLE,
                                                  role_reason='Imported existing user',
                                                  plex_server_number=server_number)
        if not response:
            await self.respond(response.issue, ctx=ctx)
        else:
            await self.respond(f"{discord_helper.mention_user(user_id=user.id)} has been imported to the database.", ctx=ctx)

    @pm_import.error
    async def pm_import_error(self, ctx, error):
        print(error)
        await self.respond("Please mention the Discord user to import to the database.", ctx=ctx)

    @pm.command(name='edit', aliases=['update', 'change'])

    async def pm_edit(self, ctx: commands.Context, username: Union[discord.Member, discord.User, str], category: str, *,
                      category_settings: str):
        """
        Update an existing Plex user's restrictions. Can edit library access, ratings and sync ability
        Does not currently support multiple Plex servers per user (defaults to first server)

        Examples:
        - pm edit username share 1 2 4 to limit 'username' to libraries 1, 2 and 4
        - pm edit username tv TV-14 to limit 'username' to up to TV-14 rated shows
        - pm edit username movie PG-13 to limit 'username' to up to PG-13 rated movies
        - pm edit username sync on to allow 'username' to sync content (offline access)
        - pm edit username movie/tv help to display available ratings
        """
        api = self.get_api(ctx=ctx)

        if isinstance(username, (discord.Member, discord.User)):
            database_user_entries = self.get_user_entries_from_database(ctx=ctx, discord_id=username.id)
        else:
            database_user_entries = self.get_user_entries_from_database(ctx=ctx, plex_username=username)


        if database_user_entries:
            database_user = database_user_entries[0]
            plex_server_number = self.get_server_numbers_user_is_on(ctx=ctx, plex_username=database_user.MediaServerUsername)
            if plex_server_number:
                plex_server_number = plex_server_number[0]
                plex_server = api.get_plex_instance(server_number=plex_server_number)
                if category == 'share':
                    if 'help' in category_settings:
                        names_and_ids = plex_server.get_defined_libraries()
                        await self.respond(
                            f"Include the numbers or names of the libraries you want {database_user.MediaServerUsername} to have access to. "
                            "Available values (case sensitive):\n" + '\n'.join(
                                names_and_ids['names']) + '\n' + '\n'.join(names_and_ids['IDs']), ctx=ctx)
                    else:
                        if plex_server.update_user_restrictions(plex_username=database_user.MediaServerUsername,
                                                                sections_to_share=category_settings):
                            await self.respond(f"{database_user.MediaServerUsername} can now only access those libraries.", ctx=ctx)
                        else:
                            await self.respond(
                                f"Sorry, I could not update the library restrictions for {database_user.MediaServerUsername}.", ctx=ctx)
                elif category == 'movie':
                    # case matters for ratings
                    if 'help' in category_settings or category_settings[0] not in px_api.all_movie_ratings:
                        await self.respond(
                            f"Available movie ratings (case sensitive): {', '.join(px_api.all_movie_ratings)}", ctx=ctx)
                    else:
                        if plex_server.update_user_restrictions(plex_username=database_user.MediaServerUsername,
                                                                rating_limit={'Movie': category_settings[0]}):
                            await self.respond(
                                f"{database_user.MediaServerUsername} is now restricted to {category_settings} and below movie ratings.", ctx=ctx)
                        else:
                            await self.respond(
                                f"Sorry, I could not update the movie rating restrictions for {database_user.MediaServerUsername}.", ctx=ctx)
                elif category in ['tv', 'show']:
                    # case matters for ratings
                    if 'help' in category_settings or category_settings[0] not in px_api.all_tv_ratings:
                        await self.respond(
                            f"Available TV show ratings (case sensitive): {', '.join(px_api.all_tv_ratings)}", ctx=ctx)
                    else:
                        if plex_server.update_user_restrictions(plex_username=database_user.MediaServerUsername,
                                                                rating_limit={'TV': category_settings[0]}):
                            await self.respond(
                                f"{database_user.MediaServerUsername} is now restricted to {category_settings} and below movie ratings.", ctx=ctx)
                        else:
                            await self.respond(
                                f"Sorry, I could not update the TV rating restrictions for {database_user.MediaServerUsername}.", ctx=ctx)
                elif category == 'sync':
                    if category_settings[0].lower() in ['yes', 'true', 'on', 'enable']:
                        if plex_server.update_user_restrictions(plex_username=database_user.MediaServerUsername,
                                                                allow_sync=True):
                            await self.respond(f"Sync is now enabled for {database_user.MediaServerUsername}.", ctx=ctx)
                        else:
                            await self.respond(f"Could not enable sync for {database_user.MediaServerUsername}.", ctx=ctx)
                    elif category_settings[0].lower() in ['no', 'false', 'off', 'disable']:
                        if plex_server.update_user_restrictions(plex_username=database_user.MediaServerUsername,
                                                                allow_sync=False):
                            await self.respond(f"Sync is now disabled for {database_user.MediaServerUsername}.", ctx=ctx)
                        else:
                            await self.respond(f"Could not disable sync for {database_user.MediaServerUsername}.", ctx=ctx)
                    else:
                        await self.respond("Please indicate 'on' or 'off' for sync setting.", ctx=ctx)
                else:
                    await self.respond(
                        "That's not a valid option. Please indicate 'share', 'movie', 'show' or 'sync'. See help for more details.", ctx=ctx)
            else:
                await self.respond("User does not have access to any Plex servers.", ctx=ctx)
        else:
            await self.respond("Could not find user in the database.", ctx=ctx)

    @pm_edit.error
    async def pm_edit_error(self, ctx, error):
        print(error)
        await discord_helper.something_went_wrong(ctx=ctx)

    @pm.command(name="winner")

    async def pm_winner(self, ctx: commands.Context, user: discord.Member, plex_username: str,
                        server_number: int = None):
        """
        Add a winner to Plex
        Mention the Discord user and their Plex username
        Include optional server_number to add to a specific server (if using multiple Plex servers)
        """
        await self.respond(
            f"Adding {plex_username} as a winner on Plex {f' (Server {server_number})' if server_number else ''}", ctx=ctx)
        response = await self.add_to_database_add_to_plex_add_role_send_dm(ctx=ctx,
                                                                      plex_username=plex_username,
                                                                      discord_id=user.id,
                                                                      user_type='Winner',
                                                                      role_name=plex_settings.WINNER_ROLE_NAME,
                                                                      role_reason='Winner added',
                                                                      dm_message="Congratulations winner, you've been invited! Check your Plex invites to accept.",
                                                                      plex_server_number=server_number)
        if not response:
            await self.respond(response.issue, ctx=ctx)
        else:
            await self.respond(
                f"{discord_helper.mention_user(user_id=user.id)}. Congratulations {plex_username}, you've been invited!", ctx=ctx)

    @pm_winner.error
    async def pm_winner_error(self, ctx, error):
        print(error)
        await self.respond("Please mention the Discord user to add to Plex, as well as their Plex username.", ctx=ctx)

    @pm.command(name="trial")

    async def pm_trial(self, ctx: commands.Context, user: discord.Member, plex_username: str,
                       server_number: int = None):
        """
        Start a Plex trial
        Mention the Discord user and their Plex username
        Include optional server_number to add to a specific server (if using multiple Plex servers)
        """
        await self.respond(
            f"Starting trial for {plex_username} on Plex {f' (Server {server_number})' if server_number else ''}", ctx=ctx)
        response = await self.add_to_database_add_to_plex_add_role_send_dm(ctx=ctx,
                                                                      plex_username=plex_username,
                                                                      discord_id=user.id,
                                                                      user_type='Trial',
                                                                      role_name=plex_settings.TRIAL_ROLE_NAME,
                                                                      role_reason='Trial started',
                                                                      dm_message="Your trial has started! Check your Plex invites to accept.",
                                                                      plex_server_number=server_number)
        if not response:
            await self.respond(response.issue, ctx=ctx)
        else:
            await self.respond(f"{discord_helper.mention_user(user_id=user.id)}. Your trial has begun, {plex_username}!", ctx=ctx)

    @pm_trial.error
    async def pm_trial_error(self, ctx, error):
        print(error)
        await self.respond("Please mention the Discord user to add to Plex, as well as their Plex username.", ctx=ctx)

    @pm.command(name="whois", aliases=["id", "find", "info"], pass_context=True)

    async def pm_whois(self, ctx: commands.Context, user: Union[discord.Member, discord.User, str]):
        """
        Find Discord or Plex user
        Currently does not support multiple Plex servers
        """
        if isinstance(user, (discord.Member, discord.User)):
            database_user_entries = self.get_user_entries_from_database(ctx=ctx, discord_id=user.id, first_only=True)
        else:
            database_user_entries = self.get_user_entries_from_database(ctx=ctx, plex_username=user, first_only=True)

        if database_user_entries:
            database_user = database_user_entries[0]
            embed_details = {
                "Discord Username": discord_helper.mention_user(user_id=database_user.DiscordID),
                "Plex Username": database_user.MediaServerUsername,
                "Server Number": database_user.WhichPlexServer,
                "Subscriber Type": database_user.SubType,
                "Payment Method": database_user.PayMethod
            }
            embed = discord_helper.generate_embed(title="User details", **embed_details)
            await self.respond(embed, ctx=ctx)
        else:
            await self.respond("User not found.", ctx=ctx)

    @pm_whois.error
    async def pm_whois_error(self, ctx, error):
        print(error)
        await discord_helper.something_went_wrong(ctx=ctx)

    @pm.command(name='details', aliases=['restrictions'], pass_context=True)

    async def pm_details(self, ctx: commands.Context, user: Union[discord.Member, discord.User, str]):
        """
        Get Plex restrictions for a user
        Does not currently support multiple Plex servers per user (defaults to first server)

        :param ctx:
        :type ctx:
        :param user:
        :type user:
        :return:
        :rtype:
        """
        api = self.get_api(ctx=ctx)

        if isinstance(user, (discord.Member, discord.User)):
            database_user_entries = self.get_user_entries_from_database(ctx=ctx, discord_id=user.id)
        else:
            database_user_entries = self.get_user_entries_from_database(ctx=ctx, plex_username=user)

        if database_user_entries:
            database_user = database_user_entries[0]
            plex_server_number = self.get_server_numbers_user_is_on(ctx=ctx, plex_username=database_user.MediaServerUsername)
            if plex_server_number:
                plex_server_number = plex_server_number[0]
                plex_server = api.get_plex_instance(server_number=plex_server_number)
                details = plex_server.get_user_restrictions(plex_username=database_user.MediaServerUsername)
                if details:
                    embed_details = {
                        "Shared Sections": ', '.join(details['sections']) if details.get('sections') else "None",
                        "Allowed Movie Ratings": ', '.join(details['filterMovies']) if details.get(
                            'filterMovies') else "All",
                        "Allowed TV Show Ratings": ', '.join(details['filterShows']) if details.get(
                            'filterShows') else "All",
                        "Sync": details.get('allowSync', 'Disabled')
                    }
                    embed = discord_helper.generate_embed(
                        title=f"Plex settings for {database_user.MediaServerUsername}", **embed_details)
                    await self.respond(embed, ctx=ctx)
                else:
                    await self.respond(
                        f"Sorry, I could not find the share settings for {database_user.MediaServerUsername}.", ctx=ctx)
            else:
                await self.respond("User does not have access to any Plex servers.", ctx=ctx)
        else:
            await self.respond("User not found.", ctx=ctx)

    @pm_details.error
    async def pm_details_error(self, ctx, error):
        print(error)
        await discord_helper.something_went_wrong(ctx=ctx)

    @commands.Cog.listener()
    async def on_ready(self):
        # self.check_trials_timer.start()
        # self.check_subs_timer.start()
        # self.check_playing.start()
        pass


def setup(bot):
    bot.add_cog(PlexManager(bot))
