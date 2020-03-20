"""
Interact with a Plex Media Server, manage users
Copyright (C) 2019 Nathan Harris
"""

import discord
from discord.ext import tasks
import requests
import asyncio
import time
from datetime import datetime
from plexapi.server import PlexServer
import plexapi
from helper.db_commands import DB
from discord.ext import commands
from media_server.plex import settings as settings
from media_server.plex import plex_api as px
import helper.discord_helper as discord_helper

plex = px.plex

db = DB(SERVER_TYPE='Plex', SQLITE_FILE=settings.SQLITE_FILE, TRIAL_LENGTH=(settings.TRIAL_LENGTH * 3600),
        BLACKLIST_FILE=settings.BLACKLIST_FILE, MULTI_PLEX=settings.MULTI_PLEX, USE_DROPBOX=settings.USE_DROPBOX)


def trial_message(startOrStop, serverNumber=None):
    if startOrStop == 'start':
        return "Hello, welcome to {}! You have been granted a {}-hour trial!".format(
            settings.PLEX_SERVER_NAME[serverNumber] if serverNumber else settings.PLEX_SERVER_NAME[0],
            str(settings.TRIAL_LENGTH))
    else:
        return "Hello, your {}-hour trial of {} has ended".format(settings.TRIAL_LENGTH, settings.PLEX_SERVER_NAME[
            serverNumber] if serverNumber else settings.PLEX_SERVER_NAME[0])


async def add_to_plex(plexname, discordId, note, serverNumber=None):
    if settings.ENABLE_BLACKLIST:
        if db.check_blacklist(plexname):
            return ['blacklist', 'username']
        if db.check_blacklist(discordId):
            return ['blacklist', 'id']
    tempPlex = plex
    if serverNumber is not None:
        tempPlex = PlexServer(settings.PLEX_SERVER_URL[serverNumber], settings.PLEX_SERVER_TOKEN[serverNumber])
    try:
        if db.add_user_to_db(discordId=discordId, username=plexname, note=note, serverNumber=serverNumber):
            tempPlex.myPlexAccount().inviteFriend(user=plexname, server=tempPlex, sections=None, allowSync=False,
                                                  allowCameraUpload=False, allowChannels=False, filterMovies=None,
                                                  filterTelevision=None, filterMusic=None)
            await asyncio.sleep(30)
            px.add_to_tautulli(serverNumber)
            if note != 't':  # Trial members do not have access to Ombi
                px.add_to_ombi()
            return [True, None]
        else:
            print("{} could not be added to the database.".format(plexname))
            return [False, None]
    except Exception as e:
        print(e)
        return [False, None]


def delete_from_plex(id):
    """
    Remove a Discord user from Plex
    Returns:
    200 - user found and removed successfully
    400 - user found in database, but not found on Plex
    600 - user found, but not removed
    700 - user not found in database
    500 - unknown error
    """
    tempPlex = plex
    serverNumber = 0
    try:
        results = db.find_user_in_db(ServerOrDiscord="Plex", data=id)
        if not results:
            return 700, serverNumber  # user not found
        plexname = results[0]
        note = results[1]
        if settings.MULTI_PLEX:
            serverNumber = results[2]
            tempPlex = PlexServer(settings.PLEX_SERVER_URL[serverNumber], settings.PLEX_SERVER_TOKEN[serverNumber])
        if not plexname:
            return 700, serverNumber  # user not found
        else:
            try:
                tempPlex.myPlexAccount().removeFriend(user=plexname)
                if note != 't':
                    px.delete_from_ombi(plexname)  # Error if trying to remove trial user that doesn't exist in Ombi?
                px.delete_from_tautulli(plexname, serverNumber)
                db.remove_user_from_db(id)
                return 200, serverNumber
            except plexapi.exceptions.NotFound:
                return 500, serverNumber  # user not found on Plex
            except Exception as e:
                print(e)
                return 400, serverNumber  # user not removed completely
    except plexapi.exceptions.NotFound:
        # print("Not found")
        return 400, serverNumber  # user not found on Plex
    except Exception as e:
        print(e)
        return 500, serverNumber  # unknown error


def remove_nonsub(memberID):
    if memberID not in settings.EXEMPT_SUBS:
        print("Ending sub for {}".format(memberID))
        return delete_from_plex(memberID)


async def backup_database():
    db.backup(file=settings.SQLITE_FILE,
              rename='backup/PlexDiscord.db.bk-{}'.format(datetime.now().strftime("%m-%d-%y")))
    db.backup(file='../blacklist.db', rename='backup/blacklist.db.bk-{}'.format(datetime.now().strftime("%m-%d-%y")))


class PlexManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def purge_winners(self, ctx):
        try:
            results = db.getWinners()
            monitorlist = []
            for u in results:
                monitorlist.append(u[0])
            print("Winners: ")
            print(monitorlist)
            data = px.t_request("get_users_table", "length=1000")
            removed_list = ""
            error_message = ""
            for i in data['response']['data']['data']:
                try:
                    if str(i['friendly_name']) in monitorlist:
                        PlexUsername = (px.t_request("get_user", "user_id=" + str(i['user_id'])))['response']['data'][
                            'username']
                        if i['duration'] is None:
                            print(PlexUsername + " has not watched anything. Purging...")
                            mention_id = await self.remove_winner(str(PlexUsername))
                            removed_list = removed_list + (mention_id if mention_id is not None else "")
                        elif i['last_seen'] is None:
                            print(PlexUsername + " has never been seen. Purging...")
                            mention_id = await self.remove_winner(str(PlexUsername))
                            removed_list = removed_list + (mention_id if mention_id is not None else "")
                        elif i['duration'] / 3600 < settings.WINNER_THRESHOLD:
                            print(PlexUsername + " has NOT met the duration requirements. Purging...")
                            mention_id = await self.remove_winner(str(PlexUsername))
                            removed_list = removed_list + (mention_id if mention_id is not None else "")
                        elif time.time() - i['last_seen'] > 1209600:
                            print(PlexUsername + " last seen too long ago. Purging...")
                            mention_id = await self.remove_winner(str(PlexUsername))
                            removed_list = removed_list + (mention_id if mention_id is not None else "")
                        else:
                            print(PlexUsername + " has met the requirements, and will not be purged.")
                except Exception as e:
                    print(e)
                    error_message = error_message + "Error checking " + str(i['friendly_name']) + ". "
                    pass
            if removed_list != "":
                await ctx.send(removed_list + "You have been removed as a Winner due to inactivity.")
            else:
                await ctx.send("No winners purged.")
            if error_message != "":
                await ctx.send(error_message)
        except Exception as e:
            print(e)
            await ctx.send("Something went wrong. Please try again later.")

    async def remove_winner(self, username):
        id = db.find_user_in_db(ServerOrDiscord="Discord", data=username)[0]
        if id is not None:
            try:
                code, num = delete_from_plex(id)
                if code == 200:
                    user = self.bot
                    await user.create_dm()
                    await user.dm_channel.send(
                        "You have been removed from " + str(settings.PLEX_SERVER_NAME[num]) + " due to inactivity.")
                    await user.remove_roles(discord.utils.get(self.bot.get_guild(int(settings.DISCORD_SERVER_ID)).roles,
                                                              name=settings.WINNER_ROLE_NAME),
                                            reason="Inactive winner")
                    db.remove_user_from_db(id)
                    return "<@" + id + ">, "
                else:
                    return None
            except plexapi.exceptions.BadRequest:
                return None
        else:
            return None

    async def check_subs(self):
        print("Checking Plex subs...")
        for member in discord_helper.get_users_without_roles(bot=self.bot, roleNames=settings.SUB_ROLES,
                                                             guildID=settings.DISCORD_SERVER_ID):
            code, num = remove_nonsub(member.id)
            if code == 700:
                print("{} was not a past Plex subscriber".format(member))
            elif code != 200:
                print("Couldn't remove {} from Plex".format(member))
        print("Plex subs check complete.")

    async def check_trials(self):
        print("Checking Plex trials...")
        trials = db.getTrials()
        trial_role = discord.utils.get(self.bot.get_guild(int(settings.DISCORD_SERVER_ID)).roles,
                                       name=settings.TRIAL_ROLE_NAME)
        for u in trials:
            print("Ending trial for " + str(u[0]))
            code, num = delete_from_plex(int(u[0]))
            if code == 200:
                try:
                    user = self.bot.get_guild(int(settings.DISCORD_SERVER_ID))
                    await user.create_dm()
                    await user.dm_channel.send(trial_message('end', num))
                    await user.remove_roles(trial_role, reason="Trial has ended.")
                except Exception as e:
                    print(e)
                    print("Trial for Discord user " + str(u[0]) + " was ended, but user could not be notified.")
            else:
                print("Failed to remove Discord user " + str(u[0]) + " from Plex.")
        print("Plex trials check complete.")

    @tasks.loop(hours=24)
    async def backup_database_timer(self):
        await backup_database()

    @tasks.loop(hours=settings.SUB_CHECK_TIME * 24)
    async def check_subs_timer(self):
        await self.check_subs()

    @tasks.loop(minutes=settings.TRIAL_CHECK_FREQUENCY)
    async def check_trials_timer(self):
        await self.check_trials()

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

    @commands.group(name="pm", aliases=["PM", "PlexMan", "plexman", "PlexManager", "plexmanager"], pass_context=True)
    async def pm(self, ctx: commands.Context):
        """
        Plex admin commands
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")

    @pm.command(name="access", pass_context=True)
    # Anyone can use this command
    async def pm_access(self, ctx: commands.Context, PlexUsername: str = None):
        """
        Check if you or another user has access to the Plex server
        """
        hasAccess = False
        serverNumber = 0
        if PlexUsername is None:
            name = db.find_user_in_db(ServerOrDiscord="Plex", data=ctx.message.author.id)[0]
        else:
            name = PlexUsername
        if name is not None:
            if settings.MULTI_PLEX:
                for i in range(0, len(settings.PLEX_SERVER_URL)):
                    tempPlex = PlexServer(settings.PLEX_SERVER_URL[i], settings.PLEX_SERVER_TOKEN[i])
                    for u in tempPlex.myPlexAccount().users():
                        if u.username == name:
                            for s in u.servers:
                                if s.name == settings.PLEX_SERVER_NAME[i] or s.name == settings.PLEX_SERVER_ALT_NAME[i]:
                                    hasAccess = True
                                    serverNumber = i
                                    break
                            break
                    break
            else:
                for u in plex.myPlexAccount().users():
                    if u.username == name:
                        for s in u.servers:
                            if s.name == settings.PLEX_SERVER_NAME[0] or s.name == settings.PLEX_SERVER_ALT_NAME[0]:
                                hasAccess = True
                                break
                        break
            if hasAccess:
                await ctx.send(("You have" if PlexUsername is None else name + " has") + " access to " + (
                    settings.PLEX_SERVER_NAME[serverNumber] if settings.MULTI_PLEX else settings.PLEX_SERVER_NAME[0]))
            else:
                await ctx.send(
                    ("You do not have" if PlexUsername is None else name + " does not have") + " access to " + (
                        "any of the Plex servers" if settings.MULTI_PLEX else settings.PLEX_SERVER_NAME[0]))
        else:
            await ctx.send("User not found.")

    @pm_access.error
    async def pm_access_error(self, ctx, error):
        print(error)
        await ctx.send("Sorry, something went wrong.")

    @pm.command(name="blacklist", aliases=['block'], pass_context=True)
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def pm_blacklist(self, ctx: commands.Context, AddOrRemove: str, DiscordUserOrPlexUsername=None):
        """
        Blacklist a Plex username or Discord ID
        """
        if DiscordUserOrPlexUsername:
            if isinstance(DiscordUserOrPlexUsername, (discord.Member, discord.User)):
                id = DiscordUserOrPlexUsername.id
            else:
                id = DiscordUserOrPlexUsername
        if AddOrRemove.lower() == 'add':
            success = db.add_to_blacklist(name_or_id=id)
            if success:
                await ctx.send("User added to blacklist.")
            else:
                await ctx.send("Something went wrong while adding user to the blacklist.")
        elif AddOrRemove.lower() == 'remove':
            success = db.remove_from_blacklist(name_or_id=id)
            if success:
                await ctx.send("User removed from blacklist.")
            else:
                await ctx.send("Something went wrong while removing user from the blacklist.")
        elif AddOrRemove.lower() == 'list':
            blacklist_entries = db.get_all_blacklist()
            await ctx.send('\n'.join([e[0] for e in blacklist_entries]))
        else:
            await ctx.send("Invalid blacklist action.")

    @pm_blacklist.error
    async def pm_blacklist_error(self, ctx, error):
        print(error)
        await ctx.send("Sorry, something went wrong.")

    @pm.command(name="status", aliases=['ping', 'up', 'online'], pass_context=True)
    # Anyone can use this command
    async def pm_status(self, ctx: commands.Context):
        """
        Check if the Plex server(s) is/are online
        """
        status = ""
        if settings.MULTI_PLEX:
            for i in range(0, len(settings.PLEX_SERVER_URL)):
                r = requests.get(settings.PLEX_SERVER_URL[i] + "/identity", timeout=10)
                if r.status_code != 200:
                    status = status + settings.PLEX_SERVER_NAME[i] + " is having connection issues right now.\n"
                else:
                    status = status + settings.PLEX_SERVER_NAME[i] + " is up and running.\n"
        else:
            r = requests.get(settings.PLEX_SERVER_URL[0] + "/identity", timeout=10)
            if r.status_code != 200:
                status = settings.PLEX_SERVER_NAME[0] + " is having connection issues right now."
            else:
                status = settings.PLEX_SERVER_NAME[0] + " is up and running."
        await ctx.send(status)

    @pm_status.error
    async def pm_status_error(self, ctx, error):
        print(error)
        await ctx.send("Sorry, I couldn't test the connection{}.".format('s' if settings.MULTI_PLEX else ""))

    @pm.command(name="winners", pass_context=True)
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def pm_winners(self, ctx: commands.Context):
        """
        List winners' Plex usernames
        """
        try:
            winners = db.getWinners()
            response = "Winners:"
            for u in winners:
                response = response + "\n" + (u[0])
            await ctx.send(response)
        except Exception as e:
            await ctx.send("Error pulling winners from database.")

    @pm.command(name="purge", pass_context=True)
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def pm_purge(self, ctx: commands.Context):
        """
        Remove inactive winners
        """
        await ctx.send("Purging winners...")
        await self.purge_winners(ctx)

    @pm_purge.error
    async def pm_purge_error(self, ctx, error):
        print(error)
        await ctx.send("Something went wrong.")

    @pm.command(name="subcheck")
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def pm_subs(self, ctx: commands.Context):
        """
        Find and removed lapsed subscribers
        This is automatically done once a week
        """
        await self.check_subs()
        await ctx.send("Sub check complete.")

    @pm_subs.error
    async def pm_subs_error(self, ctx, error):
        print(error)
        await ctx.send("Something went wrong.")

    @pm.command(name="trialcheck")
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def pm_trial_check(self, ctx: commands.Context):
        """
        Find and remove lapsed trials
        This is automatically done at the interval set in Settings
        """
        await self.check_trials()
        await ctx.send("Trial check complete.")

    @pm_trial_check.error
    async def pm_trial_check_error(self, ctx, error):
        print(error)
        await ctx.send("Something went wrong.")

    @pm.command(name="cleandb", aliases=["clean", "scrub", "syncdb"], pass_context=True)
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def pm_cleandb(self, ctx: commands.Context):
        """
        Remove old users from database
        If you delete a user from Plex directly,
        run this to remove the user's entry in the
        Plex user database.
        """
        existingUsers = px.getPlexFriends()
        dbEntries = db.get_all_entries_in_db()
        if dbEntries:
            deletedUsers = ""
            for entry in dbEntries:
                if entry[1].lower() not in existingUsers:  # entry[1] is PlexUsername, compare lowercase to
                    # existingUsers (returned as lowercase)
                    deletedUsers += entry[1] + "\n"
                    print("Deleting " + str(entry[1]) + " from the Plex database...")
                    # db.remove_user_from_db(entry[0])  # entry[0] is DiscordID
            if deletedUsers:
                await ctx.send("The following users were deleted from the database:\n" + deletedUsers[:-1])
            else:
                await ctx.send("No old users found and removed from database.")
        else:
            await ctx.send("An error occurred when grabbing users from the database.")

    @pm_cleandb.error
    async def pm_cleandb_error(self, ctx, error):
        print(error)
        await ctx.send("Something went wrong.")

    @pm.command(name="backupdb")
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def pm_backupdb(self, ctx: commands.Context):
        """
        Backup the database to Dropbox.
        This is automatically done every 24 hours.
        """
        await backup_database()
        await ctx.send("Backup complete.")

    @pm_backupdb.error
    async def pm_backupdb_error(self, ctx, error):
        print(error)
        await ctx.send("Something went wrong.")

    @pm.command(name="count")
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def pm_count(self, ctx: commands.Context, serverNumber: int = None):
        """
        Check Plex share count
        Include optional serverNumber to check a specific Plex server (if using multiple servers)
        """
        if settings.MULTI_PLEX:
            if serverNumber is None:
                totals = ""
                for i in range(0, len(settings.PLEX_SERVER_URL)):
                    totals = totals + settings.PLEX_SERVER_NAME[i] + " has " + str(px.countServerSubs(i)) + " users\n"
                await ctx.send(totals)
            else:
                if serverNumber <= len(settings.PLEX_SERVER_URL):
                    await ctx.send(settings.PLEX_SERVER_NAME[serverNumber - 1] + " has " + str(
                        px.countServerSubs(serverNumber - 1)) + " users")
                else:
                    await ctx.send("That server number does not exist.")
        else:
            await ctx.send(settings.PLEX_SERVER_NAME[0] + " has " + str(px.countServerSubs()) + " users")

    @pm_count.error
    async def pm_count_error(self, ctx, error):
        print(error)
        await ctx.send("Something went wrong. Please try again later.")

    @pm.command(name="add", alias=["invite", "new"], pass_context=True)
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def pm_add(self, ctx: commands.Context, user: discord.Member, PlexUsername: str, serverNumber: int = None):
        """
        Add a Discord user to Plex
        Mention the Discord user and their Plex username
        Include optional serverNumber to add to a specific server (if using multiple Plex servers)
        """
        if settings.MULTI_PLEX:
            if serverNumber is None:  # No specific number indicated. Defaults adding to the least-fill server
                serverNumber = px.getSmallestServer()
            elif serverNumber > len(settings.PLEX_SERVER_URL):
                await ctx.send("That server number does not exist.")
            else:
                serverNumber = serverNumber - 1  # user's "server 5" is really server 4 in the index
            await ctx.send('Adding ' + PlexUsername + ' to ' + settings.PLEX_SERVER_NAME[
                serverNumber] + '. Please wait about 30 seconds...')
            try:
                note = 's'
                if discord.utils.get(self.bot.get_guild(int(settings.DISCORD_SERVER_ID)).roles,
                                     name=settings.WINNER_ROLE_NAME) in user.roles:
                    note = 'w'
                added = await add_to_plex(PlexUsername, user.id, note, serverNumber)
                if added[0] and not added[1]:
                    role = discord.utils.get(ctx.message.guild.roles, name=settings.AFTER_APPROVED_ROLE_NAME)
                    await user.add_roles(role, reason="Access membership channels")
                    await ctx.send(
                        user.mention + " You've been invited, " + PlexUsername + ". Welcome to " +
                        settings.PLEX_SERVER_NAME[
                            serverNumber] + "!")
                elif added[1]:
                    await ctx.send("That {} is blacklisted.".format(added[1]))
                else:
                    await ctx.send(user.name + " could not be added to that server.")
            except plexapi.exceptions.BadRequest:
                await ctx.send(PlexUsername + " is not a valid Plex username.")
        else:
            await ctx.send(
                'Adding ' + PlexUsername + ' to ' + settings.PLEX_SERVER_NAME[0] + '. Please wait about 30 seconds...')
            try:
                note = 's'
                if discord.utils.get(self.bot.get_guild(int(settings.DISCORD_SERVER_ID)).roles,
                                     name=settings.WINNER_ROLE_NAME) in user.roles:
                    note = 'w'
                added = await add_to_plex(PlexUsername, user.id, note, serverNumber)
                if added[0] and not added[1]:
                    role = discord.utils.get(ctx.message.guild.roles, name=settings.AFTER_APPROVED_ROLE_NAME)
                    await user.add_roles(role, reason="Access membership channels")
                    await ctx.send(
                        user.mention + " You've been invited, " + PlexUsername + ". Welcome to " +
                        settings.PLEX_SERVER_NAME[0] + "!")
                elif added[1]:
                    await ctx.send("That {} is blacklisted.".format(added[1]))
                else:
                    await ctx.send(user.name + " could not be added to Plex.")
            except plexapi.exceptions.BadRequest:
                await ctx.send(PlexUsername + " is not a valid Plex username.")

    @pm_add.error
    async def pm_add_error(self, ctx, error):
        print(error)
        await ctx.send("Please mention the Discord user to add to Plex, as well as their Plex username.")

    @pm.command(name="remove", alias=["uninvite", "delete", "rem"])
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def pm_remove(self, ctx: commands.Context, user: discord.Member):
        """
        Remove a Discord user from Plex
        """
        code, num = delete_from_plex(user.id)
        if code == 200:
            role = discord.utils.get(ctx.message.guild.roles, name=settings.AFTER_APPROVED_ROLE_NAME)
            await user.remove_roles(role, reason="Removed from Plex")
            await ctx.send("You've been removed from " + (
                settings.PLEX_SERVER_NAME[
                    num] if settings.MULTI_PLEX else settings.PLEX_SERVER_NAME[0]) + ", " + user.mention + ".")
        else:
            await ctx.send("User could not be removed.")

    @pm_remove.error
    async def pm_remove_error(self, ctx, error):
        print(error)
        await ctx.send("Please mention the Discord user to remove from Plex.")

    @pm.command(name="trial")
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def pm_trial(self, ctx: commands.Context, user: discord.Member, PlexUsername: str, serverNumber: int = None):
        """
        Start a Plex trial
        """
        if settings.MULTI_PLEX:
            if serverNumber is None:  # No specific number indicated. Defaults adding to the least-fill server
                serverNumber = px.getSmallestServer()
            elif serverNumber > len(settings.PLEX_SERVER_URL):
                await ctx.send("That server number does not exist.")
            else:
                serverNumber = serverNumber - 1  # user's "server 5" is really server 4 in the index
            await ctx.send('Adding ' + PlexUsername + ' to ' + settings.PLEX_SERVER_NAME[
                serverNumber] + '. Please wait about 30 seconds...')
            try:
                added = await add_to_plex(PlexUsername, user.id, 't', serverNumber)
                if added[0] and not added[1]:
                    role = discord.utils.get(ctx.message.guild.roles, name=settings.TRIAL_ROLE_NAME)
                    await user.add_roles(role, reason="Trial started.")
                    await user.create_dm()
                    await user.dm_channel.send(trial_message('start', serverNumber))
                    await ctx.send(
                        user.mention + ", your trial has begun. Please check your Direct Messages for details.")
                elif added[1]:
                    await ctx.send("That {} is blacklisted.".format(added[1]))
                else:
                    await ctx.send(user.name + " could not be added to that server.")
            except plexapi.exceptions.BadRequest:
                await ctx.send(PlexUsername + " is not a valid Plex username.")
        else:
            await ctx.send(
                'Starting ' + settings.PLEX_SERVER_NAME[
                    0] + ' trial for ' + PlexUsername + '. Please wait about 30 seconds...')
            try:
                added = await add_to_plex(PlexUsername, user.id, 't')
                if added[0] and not added[1]:
                    role = discord.utils.get(ctx.message.guild.roles, name=settings.TRIAL_ROLE_NAME)
                    await user.add_roles(role, reason="Trial started.")
                    await user.create_dm()
                    await user.dm_channel.send(trial_message('start'))
                    await ctx.send(
                        user.mention + ", your trial has begun. Please check your Direct Messages for details.")
                elif added[1]:
                    await ctx.send("That {} is blacklisted.".format(added[1]))
                else:
                    await ctx.send(user.name + " could not be added to Plex.")
            except plexapi.exceptions.BadRequest:
                await ctx.send(PlexUsername + " is not a valid Plex username.")

    @pm_trial.error
    async def pm_trial_error(self, ctx, error):
        print(error)
        await ctx.send("Please mention the Discord user to add to Plex, as well as their Plex username.")

    @pm.command(name="import", pass_context=True)
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def pm_import(self, ctx: commands.Context, user: discord.Member, PlexUsername: str, subType: str,
                        serverNumber: int = None):
        """
        Add existing Plex users to the database.
        user - tag a Discord user
        PlexUsername - Plex username or email of the Discord user
        subType - custom note for tracking subscriber type; MUST be less than 5 letters.
        Default in database: 's' for Subscriber, 'w' for Winner, 't' for Trial.
        NOTE: subType 't' will make a new 24-hour timestamp for the user.
        """
        if len(subType) > 4:
            await ctx.send("subType must be less than 5 characters long.")
        elif serverNumber is not None and serverNumber > len(settings.PLEX_SERVER_URL):
            await ctx.send("That server number does not exist.")
        else:
            new_entry = db.add_user_to_db(discordId=user.id, username=PlexUsername, note=subType,
                                          serverNumber=serverNumber)
            if new_entry:
                if subType == 't':
                    await ctx.send("Trial user was added/new timestamp issued.")
                else:
                    await ctx.send("User added to the database.")
            else:
                await ctx.send("User already exists in the database.")

    @pm_import.error
    async def pm_import_error(self, ctx, error):
        print(error)
        await ctx.send(
            "Please mention the Discord user to add to the database, including their Plex username and sub type.")

    @pm.group(name="find", aliases=["id"], pass_context=True)
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def pm_find(self, ctx: commands.Context):
        """
        Find Discord or Plex user
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")

    @pm_find.command(name="plex", aliases=["p"])
    async def pm_find_plex(self, ctx: commands.Context, user: discord.Member):
        """
        Find Discord member's Plex username
        """
        results = db.find_user_in_db(ServerOrDiscord="Plex", data=user.id)
        name = results[0]
        note = results[1]
        num = None
        if settings.MULTI_PLEX:
            num = results[2]
        if name is not None:
            await ctx.send(user.mention + " is Plex user: " + name + (" [Trial" if note == 't' else " [Subscriber") + (
                " - Server " + str(num) if settings.MULTI_PLEX else "") + "]")
        else:
            await ctx.send("User not found.")

    @pm_find.command(name="discord", aliases=["d"])
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def pm_find_discord(self, ctx: commands.Context, PlexUsername: str):
        """
        Find Plex user's Discord name
        """
        id = db.find_user_in_db(ServerOrDiscord="Discord", data=PlexUsername)[0]
        if id is not None:
            await ctx.send(PlexUsername + " is Discord user: " + self.bot.get_user(int(id)).mention)
        else:
            await ctx.send("User not found.")

    @pm_find.error
    async def pm_find_error(self, ctx, error):
        print(error)
        await ctx.send("An error occurred while looking for that user.")

    @pm.group(name="info")
    async def pm_info(self, ctx: commands.Context):
        """
        Get database entry for a user
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")

    @pm_info.command(name="plex", aliases=["p"])
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def pm_info_plex(self, ctx, PlexUsername: str):
        """
        Get database entry for Plex username
        """
        embed = discord.Embed(title=("Info for " + str(PlexUsername)))
        n = db.describe_table(file=settings.SQLITE_FILE, table="users")
        d = db.find_entry_in_db(fieldType="PlexUsername", data=PlexUsername)
        if d:
            for i in range(0, len(n)):
                val = str(d[i])
                if str(n[i][1]) == "DiscordID":
                    val = val + " (" + self.bot.get_user(int(d[i])).mention + ")"
                if str(n[i][1]) == "Note":
                    val = ("Trial" if d[i] == 't' else "Subscriber")
                if settings.MULTI_PLEX and str(n[i][1]) == "ServerNum":
                    val = ("Server Number: " + d[i])
                if d[i] is not None:
                    embed.add_field(name=str(n[i][1]), value=val, inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send("That user is not in the database.")

    @pm_info.command(name="discord", aliases=["d"])
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def pm_info_discord(self, ctx, user: discord.Member):
        """
        Get database entry for Discord user
        """
        embed = discord.Embed(title=("Info for " + user.name))
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
                if settings.MULTI_PLEX and str(n[i][1]) == "ServerNum":
                    val = ("Server Number: " + d[i])
                if d[i] is not None:
                    embed.add_field(name=str(n[i][1]), value=val, inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send("That user is not in the database.")

    @pm_info.error
    async def pm_info_error(self, ctx, error):
        print(error)
        await ctx.send("User not found.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if settings.AUTO_WINNERS:
            if message.author.id == settings.GIVEAWAY_BOT_ID and "congratulations" in message.content.lower() and message.mentions:
                tempWinner = discord.utils.get(message.guild.roles, name=settings.TEMP_WINNER_ROLE_NAME)
                for u in message.mentions:
                    await u.add_roles(tempWinner, reason="Winner - access winner invite channel")
            if message.channel.id == settings.WINNER_CHANNEL and discord.utils.get(message.guild.roles,
                                                                                   name=settings.TEMP_WINNER_ROLE_NAME) in message.author.roles:
                plexname = message.content.strip()  # Only include username, nothing else
                await message.channel.send(
                    "Adding " + plexname + ". Please wait about 30 seconds...\n"
                                           "Be aware, you will be removed from this channel once you are added "
                                           "successfully.")
                try:
                    serverNumber = None
                    if settings.MULTI_PLEX:
                        serverNumber = px.getSmallestServer()
                    await add_to_plex(plexname, message.author.id, 'w', serverNumber)
                    await message.channel.send(
                        message.author.mention + " You've been invited, " + plexname + ". Welcome to " +
                        settings.PLEX_SERVER_NAME[serverNumber] + "!")
                    await message.author.remove_roles(
                        discord.utils.get(message.guild.roles, name=settings.TEMP_WINNER_ROLE_NAME),
                        reason="Winner was processed successfully.")
                except plexapi.exceptions.BadRequest:
                    await message.channel.send(
                        message.author.mention + ", " + plexname + " is not a valid Plex username.")

    @commands.Cog.listener()
    async def on_ready(self):
        self.check_trials_timer.start()
        self.check_subs_timer.start()
        self.check_playing.start()

    def __init__(self, bot):
        self.bot = bot
        print("Plex Manager ready to go.")


def setup(bot):
    bot.add_cog(PlexManager(bot))
