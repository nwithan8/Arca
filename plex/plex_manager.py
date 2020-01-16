"""
Interact with a Plex Media Server, manage users
Copyright (C) 2019 Nathan Harris
"""

import discord
from discord.ext import commands, tasks
import requests
import asyncio
import time
from plexapi.server import PlexServer
import plexapi
from plexapi.myplex import MyPlexAccount
from plex.db_commands import DB
import urllib
import json
import re
from discord.ext import commands
import sys, traceback, os

# Database Schema:
# PlexDiscord.users
# (DiscordID BIGINT, PlexUsername 'VARCHAR(100)', PlexEmail 'VARCHAR(320)', ServerNum INT, ExpirationStamp INT, Note 'VARCHAR(5)')

# Discord-to-Plex database (SQLite3)
SQLITE_FILE = '/nwithan8-cogs/plex_manager/PlexDiscord.db'  # File path + name + extension (i.e.
# "/root/nwithan8-cogs/plex_manager/PlexDiscord.db"

MULTI_PLEX = False

# fill out below if using MULTI_PLEX
PLEX_SERVER_URL = os.environ.get('PLEX_URL')
PLEX_SERVER_TOKEN = os.environ.get('PLEX_TOKEN')
PLEX_SERVER_NAME = os.environ.get('PLEX_SERVER_NAME')
PLEX_SERVER_ALT_NAME = os.environ.get('PLEX_SERVER_ALT_NAME')
plex = ""  # Blank variable, do not edit

if MULTI_PLEX:
    PLEX_SERVER_URL = []
    PLEX_SERVER_TOKEN = []
    PLEX_SERVER_NAME = []
    PLEX_SERVER_ALT_NAME = []
    plex = PlexServer(PLEX_SERVER_URL[0], PLEX_SERVER_TOKEN[0])
else:
    plex = PlexServer(PLEX_SERVER_URL, PLEX_SERVER_TOKEN)

# Ombi settings
USE_OMBI = False

# Tautulli settings
USE_TAUTULLI = True
TAUTULLI_URL = os.environ.get('TAUTULLI_URL')
TAUTULLI_KEY = os.environ.get('TAUTULLI_KEY')

MULTI_TAUTULLI = False
if MULTI_TAUTULLI:
    TAUTULLI_URL = []
    TAUTULLI_KEY = []

# Discord (Admin) settings
SERVER_ID = os.environ.get('DISCORD_SERVER_ID')
ADMIN_ID = os.environ.get('ADMIN_ID')
ADMIN_ROLE_NAME = "Admin"
AFTER_APPROVED_ROLE_NAME = "Invited"
subRoles = ["Monthly Subscriber", "Yearly Subscriber", "Winner", "Bot"]  # Exempt from removal
exemptsubs = [ADMIN_ID]  # Discord IDs for users exempt from subscriber checks/deletion, separated by commas
SUB_CHECK_TIME = 7  # days

# Trial settings
TRIAL_ROLE_NAME = "Trial Member"
TRIAL_LENGTH = 24  # hours
TRIAL_CHECK_FREQUENCY = 15  # minutes

# Winner settings
WINNER_ROLE_NAME = "Winner"
WINNER_THRESHOLD = 2  # hours
AUTO_WINNERS = False
# True: Messages from the indicated GIVEAWAY_BOT_ID user will be scanned for mentioned Discord users (winners). The
# winners will be auto-assigned the TEMP_WINNER_ROLE_NAME. That role gives them access to a specified WINNER_CHANNEL
# channel Users then post their Plex username (ONLY their Plex username) in the channel, which is processed by the
# bot. The bot invites the Plex username, and associates the Discord user author of the message with the Plex
# username in the database. The user is then have the TEMP_WINNER_ROLE_NAME role removed (which removes them from the
# WINNER_CHANNEL channel), and assigned the final WINNER_ROLE_NAME role.
TEMP_WINNER_ROLE_NAME = "Uninvited Winner"
WINNER_CHANNEL = 0  # Channel ID
GIVEAWAY_BOT_ID = 0

# DO NOT EDIT
if USE_OMBI:
    OMBI_URL = os.environ.get('OMBI_URL') + "/api/v1/"
    ombi_import = OMBI_URL + 'Job/plexuserimporter'
    ombi_users = OMBI_URL + 'Identity/Users'
    ombi_delete = OMBI_URL + 'Identity/'
    ombi_movie_count = OMBI_URL + 'Request/movie/total'
    ombi_movie_id = OMBI_URL + 'Request/movie/1/'
    ombi_approve_movie = OMBI_URL + 'Request/movie/approve'
    ombi_tv_count = OMBI_URL + 'Request/tv/total'
    ombi_tv_id = OMBI_URL + 'Request/tv/1/'
    ombi_approve_tv = OMBI_URL + 'Request/tv/approve'
    approve_header = {'ApiKey': os.environ.get('OMBI_KEY'), 'accept': 'application/json',
                      'Content-Type': 'application/json-patch+json'}
    ombi_headers = {'ApiKey': os.environ.get('OMBI_KEY')}

db = DB(SQLITE_FILE, MULTI_PLEX, TRIAL_LENGTH)


# Code below #

def trial_message(type, serverNumber=None):
    if type == 'start':
        return "Hello, welcome to " + (PLEX_SERVER_NAME[
                                           serverNumber] if serverNumber else PLEX_SERVER_NAME) + "! You have been granted a " + str(
            TRIAL_LENGTH) + "-hour trial!"
    else:
        return "Hello, your " + str(TRIAL_LENGTH) + "-hour trial of " + (
            PLEX_SERVER_NAME[serverNumber] if serverNumber else PLEX_SERVER_NAME) + " has ended."


def countServerSubs(serverNumber):
    tempPlex = plex
    tempServerName = PLEX_SERVER_NAME
    tempServerAltName = PLEX_SERVER_ALT_NAME
    if serverNumber >= 0:
        tempPlex = PlexServer(PLEX_SERVER_URL[serverNumber], PLEX_SERVER_TOKEN[serverNumber])
        tempServerName = PLEX_SERVER_NAME[serverNumber]
        tempServerAltName = PLEX_SERVER_ALT_NAME[serverNumber]
    count = 0
    for u in tempPlex.myPlexAccount().users():
        for s in u.servers:
            if s.name == tempServerName or s.name == tempServerAltName:
                count += 1
    return count


def getSmallestServer():
    serverNumber = 0
    smallestCount = 100
    for i in len(0, PLEX_SERVER_URL):
        tempCount = countServerSubs(i)
        if tempCount < smallestCount:
            serverNumber = i
            smallestCount = tempCount
    return serverNumber


def get_plex_users(serverNumber=None):
    """
    Returns all usernames (lowercase for comparison)
    """
    users = []
    tempPlex = plex
    tempServerName = PLEX_SERVER_NAME
    tempServerAltName = PLEX_SERVER_ALT_NAME
    if MULTI_PLEX:
        if serverNumber:  # from specific server
            tempPlex = PlexServer(PLEX_SERVER_URL[serverNumber], PLEX_SERVER_TOKEN[serverNumber])
            tempServerName = PLEX_SERVER_NAME[serverNumber]
            tempServerAltName = PLEX_SERVER_ALT_NAME[serverNumber]
            for u in tempPlex.myPlexAccount().users():
                for s in u.servers:
                    if s.name == tempServerName or s.name == tempServerAltName:
                        users.append(u.username.lower())
        else:  # from all servers
            for serverNumber in range(len(PLEX_SERVER_URL)):
                tempPlex = PlexServer(PLEX_SERVER_URL[serverNumber], PLEX_SERVER_TOKEN[serverNumber])
                tempServerName = PLEX_SERVER_NAME[serverNumber]
                tempServerAltName = PLEX_SERVER_ALT_NAME[serverNumber]
                for u in tempPlex.myPlexAccount().users():
                    for s in u.servers:
                        if s.name == tempServerName or s.name == tempServerAltName:
                            users.append(u.username.lower())
    else:  # from the single server
        for u in tempPlex.myPlexAccount().users():
            for s in u.servers:
                if s.name == tempServerName or s.name == tempServerAltName:
                    users.append(u.username.lower())
    return users


class PlexManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def t_request(cmd, params, serverNumber=None):
        return json.loads(requests.get('{url}/api/v2?apikey={key}&cmd={cmd}{params}'.format(url=(TAUTULLI_URL[serverNumber] if serverNumber is not None else TAUTULLI_URL), key=(TAUTULLI_KEY[serverNumber] if serverNumber is not None else TAUTULLI_KEY), cmd=cmd, params=("&" + str(params)) if params is not None else "")).text)

    def add_to_tautulli(self, serverNumber=None):
        if not USE_TAUTULLI:
            pass
        else:
            response = self.t_request("refresh_users_list", None, serverNumber)

    def delete_from_tautulli(self, plexname, serverNumber=None):
        if not USE_TAUTULLI:
            pass
        else:
            response = self.t_request("delete_user", "user_id={plexname}".format(str(plexname)), serverNumber)

    @staticmethod
    def add_to_ombi():
        if not USE_OMBI:
            pass
        else:
            requests.post(ombi_import, headers=ombi_headers)

    @staticmethod
    def delete_from_ombi(plexname):
        if not USE_OMBI:
            pass
        else:
            data = requests.get(ombi_users, headers=ombi_headers).json()
            id = ""
            for i in data:
                if i['userName'].lower() == plexname:
                    id = i['id']
            delete = str(ombi_delete) + str(id)
            requests.delete(delete, headers=ombi_headers)

    async def add_to_plex(self, plexname, discordId, note, serverNumber=None):
        tempPlex = plex
        if serverNumber is not None:
            tempPlex = PlexServer(PLEX_SERVER_URL[serverNumber], PLEX_SERVER_TOKEN[serverNumber])
        try:
            if db.add_user_to_db(discordId, plexname, note, serverNumber):
                tempPlex.myPlexAccount().inviteFriend(user=plexname, server=tempPlex, sections=None, allowSync=False,
                                                      allowCameraUpload=False, allowChannels=False, filterMovies=None,
                                                      filterTelevision=None, filterMusic=None)
                await asyncio.sleep(30)
                self.add_to_tautulli(serverNumber)
                if note != 't':  # Trial members do not have access to Ombi
                    self.add_to_ombi()
                return True
            else:
                print("{} could not be added to the database.".format(plexname))
                return False
        except Exception as e:
            print(e)
            return False

    def delete_from_plex(self, id):
        tempPlex = plex;
        serverNumber = 0
        try:
            results = db.find_user_in_db("Plex", id)
            plexname = results[0]
            note = results[1]
            if MULTI_PLEX:
                serverNumber = results[2]
                tempPlex = PlexServer(PLEX_SERVER_URL[serverNumber], PLEX_SERVER_TOKEN[serverNumber])
            if plexname is not None:
                tempPlex.myPlexAccount().removeFriend(user=plexname)
                if note != 't':
                    self.delete_from_ombi(plexname)  # Error if trying to remove trial user that doesn't exist in Ombi?
                self.delete_from_tautulli(plexname, serverNumber)
                db.remove_user_from_db(id)
                return True, serverNumber
            else:
                return False, serverNumber
        except plexapi.exceptions.NotFound:
            # print("Not found")
            return False, serverNumber

    async def purge_winners(self, ctx):
        try:
            results = db.getWinners()
            monitorlist = []
            for u in results:
                monitorlist.append(u[0])
            print("Winners: ")
            print(monitorlist)
            data = self.t_request("get_users_table", "length=1000")
            removed_list = ""
            error_message = ""
            for i in data['response']['data']['data']:
                try:
                    if str(i['friendly_name']) in monitorlist:
                        PlexUsername = (self.t_request("get_user", "user_id=" + str(i['user_id'])))['response']['data'][
                            'username']
                        if i['duration'] is None:
                            print(PlexUsername + " has not watched anything. Purging...")
                            mention_id = await self.remove_winner(str(PlexUsername))
                            removed_list = removed_list + (mention_id if mention_id is not None else "")
                        elif i['last_seen'] is None:
                            print(PlexUsername + " has never been seen. Purging...")
                            mention_id = await self.remove_winner(str(PlexUsername))
                            removed_list = removed_list + (mention_id if mention_id is not None else "")
                        elif i['duration'] / 3600 < WINNER_THRESHOLD:
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
        id = db.find_user_in_db("Discord", username)[0]
        if id is not None:
            try:
                self.delete_from_plex(id)
                user = self.bot.get_user(int(id))
                await user.create_dm()
                await user.dm_channel.send(
                    "You have been removed from " + str(PLEX_SERVER_NAME) + " due to inactivity.")
                await user.remove_roles(discord.utils.get(self.bot.get_guild(int(SERVER_ID)).roles, name="Winner"),
                                        reason="Inactive winner")
                db.remove_user_from_db(id)
            except plexapi.exceptions.BadRequest:
                pass
            return "<@" + id + ">, "
        else:
            return None

    def remove_nonsub(self, memberID):
        if memberID not in exemptsubs:
            self.delete_from_plex(memberID)

    @tasks.loop(seconds=SUB_CHECK_TIME * (3600 * 24))
    async def check_subs(self):
        print("Checking Plex subs...")
        exemptRoles = []
        allRoles = self.bot.get_guild(int(SERVER_ID)).roles
        for r in allRoles:
            if r.name in subRoles:
                exemptRoles.append(r)
        for member in self.bot.get_guild(int(SERVER_ID)).members:
            if not any(x in member.roles for x in exemptRoles):
                self.remove_nonsub(member.id)
        print("Plex subs check complete.")

    @tasks.loop(seconds=TRIAL_CHECK_FREQUENCY * 60)
    async def check_trials(self):
        print("Checking Plex trials...")
        trials = db.getTrials()
        trial_role = discord.utils.get(self.bot.get_guild(int(SERVER_ID)).roles, name=TRIAL_ROLE_NAME)
        for u in trials:
            print("Ending trial for " + str(u[0]))
            success, num = self.delete_from_plex(int(u[0]))
            if success:
                try:
                    user = self.bot.get_guild(int(SERVER_ID)).get_member(int(u[0]))
                    await user.create_dm()
                    await user.dm_channel.send(trial_message('end', num))
                    await user.remove_roles(trial_role, reason="Trial has ended.")
                except Exception as e:
                    print(e)
                    print("Trial for Discord user " + str(u[0]) + " was ended, but user could not be notified.")
            else:
                print("Failed to remove Discord user " + str(u[0]) + " from Plex.")
        print("Plex trials check complete.")

    @commands.group(name="pm", aliases=["PM", "PlexMan", "plexman"], pass_context=True)
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
            name = db.find_user_in_db("Plex", ctx.message.author.id)[0]
        else:
            name = PlexUsername
        if name is not None:
            if MULTI_PLEX:
                for i in range(0, len(PLEX_SERVER_URL)):
                    tempPlex = PlexServer(PLEX_SERVER_URL[i], PLEX_SERVER_TOKEN[i])
                    for u in tempPlex.myPlexAccount().users():
                        if u.username == name:
                            for s in u.servers:
                                if s.name == PLEX_SERVER_NAME[i] or s.name == PLEX_SERVER_ALT_NAME[i]:
                                    hasAccess = True
                                    serverNumber = i
                                    break
                            break
                    break
            else:
                for u in plex.myPlexAccount().users():
                    if u.username == name:
                        for s in u.servers:
                            if s.name == PLEX_SERVER_NAME or s.name == PLEX_SERVER_ALT_NAME:
                                hasAccess = True
                                break
                        break
            if hasAccess:
                await ctx.send(("You have" if PlexUsername is None else name + " has") + " access to " + (
                    PLEX_SERVER_NAME[serverNumber] if MULTI_PLEX else PLEX_SERVER_NAME))
            else:
                await ctx.send(
                    ("You do not have" if PlexUsername is None else name + " does not have") + " access to " + (
                        "any of the Plex servers" if MULTI_PLEX else PLEX_SERVER_NAME))
        else:
            await ctx.send("User not found.")

    @pm_access.error
    async def pm_access_error(self, ctx, error):
        print(error)
        await ctx.send("Sorry, something went wrong.")

    @pm.command(name="status", aliases=['ping', 'up', 'online'], pass_context=True)
    async def pm_status(self, ctx: commands.Context):
        """
        Check if the Plex server(s) is/are online
        """
        status = ""
        if MULTI_PLEX:
            for i in range(0, len(PLEX_SERVER_URL)):
                r = requests.get(PLEX_SERVER_URL[i] + "/identity", timeout=10)
                if r.status_code != 200:
                    status = status + PLEX_SERVER_NAME[i] + " is having connection issues right now.\n"
                else:
                    status = status + PLEX_SERVER_NAME[i] + " is up and running.\n"
        else:
            r = requests.get(PLEX_SERVER_URL + "/identity", timeout=10)
            if r.status_code != 200:
                status = PLEX_SERVER_NAME + " is having connection issues right now."
            else:
                status = PLEX_SERVER_NAME + " is up and running."
        await ctx.send(status)

    @pm_status.error
    async def pm_status_error(self, ctx, error):
        print(error)
        await ctx.send("Sorry, I couldn't test the " + ("connections." if MULTI_PLEX else "connection."))

    @pm.command(name="winners", pass_context=True)
    @commands.has_role(ADMIN_ROLE_NAME)
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
    @commands.has_role(ADMIN_ROLE_NAME)
    async def pm_purge(self, ctx: commands.Context):
        """
        Remove inactive winners
        """
        await ctx.send("Purging winners...")
        await self.purge_winners(ctx)

    @pm.command(name="cleandb", aliases=["clean", "scrub", "syncdb"], pass_context=True)
    async def pm_cleandb(self, ctx: commands.Context):
        """
        Remove old users from database
        If you delete a user from Plex directly,
        run this to remove the user's entry in the
        Plex user database.
        """
        existingUsers = get_plex_users()
        dbEntries = db.get_all_entries_in_db()
        if dbEntries:
            deletedUsers = ""
            for entry in dbEntries:
                if entry[1].lower() not in existingUsers:  # entry[1] is PlexUsername, compare lowercase to
                    # existingUsers (returned as lowercase)
                    deletedUsers += entry[1] + "\n"
                    print("Deleting " + str(entry[1]) + " from the Plex database...")
                    db.remove_user_from_db(entry[0])  # entry[0] is DiscordID
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

    @pm.command(name="count")
    @commands.has_role(ADMIN_ROLE_NAME)
    async def pm_count(self, ctx: commands.Context, serverNumber: int = None):
        """
        Check Plex share count
        Include optional serverNumber to check a specific Plex server (if using multiple servers)
        """
        if MULTI_PLEX:
            if serverNumber is None:
                totals = ""
                for i in range(0, len(PLEX_SERVER_URL)):
                    totals = totals + PLEX_SERVER_NAME[i] + " has " + str(countServerSubs(i)) + " users\n"
                await ctx.send(totals)
            else:
                if serverNumber <= len(PLEX_SERVER_URL):
                    await ctx.send(PLEX_SERVER_NAME[serverNumber - 1] + " has " + str(
                        countServerSubs(serverNumber - 1)) + " users")
                else:
                    await ctx.send("That server number does not exist.")
        else:
            await ctx.send(PLEX_SERVER_NAME + " has " + str(countServerSubs(-1)) + " users")

    @pm_count.error
    async def pm_count_error(self, ctx, error):
        print(error)
        await ctx.send("Something went wrong. Please try again later.")

    @pm.command(name="add", alias=["invite", "new"], pass_context=True)
    @commands.has_role(ADMIN_ROLE_NAME)
    async def pm_add(self, ctx: commands.Context, user: discord.Member, PlexUsername: str, serverNumber: int = None):
        """
        Add a Discord user to Plex
        Mention the Discord user and their Plex username
        Include optional serverNumber to add to a specific server (if using multiple Plex servers)
        """
        added = False
        if MULTI_PLEX:
            if serverNumber is None:  # No specific number indicated. Defaults adding to the least-fill server
                serverNumber = getSmallestServer()
            elif serverNumber > len(PLEX_SERVER_URL):
                await ctx.send("That server number does not exist.")
            else:
                serverNumber = serverNumber - 1  # user's "server 5" is really server 4 in the index
            await ctx.send('Adding ' + PlexUsername + ' to ' + PLEX_SERVER_NAME[
                serverNumber] + '. Please wait about 30 seconds...')
            try:
                added = await self.add_to_plex(PlexUsername, user.id, 's', serverNumber)
                if added:
                    role = discord.utils.get(ctx.message.guild.roles, name=AFTER_APPROVED_ROLE_NAME)
                    await user.add_roles(role, reason="Access membership channels")
                    await ctx.send(
                        user.mention + " You've been invited, " + PlexUsername + ". Welcome to " + PLEX_SERVER_NAME[
                            serverNumber] + "!")
                else:
                    await ctx.send(user.name + " could not be added to that server.")
            except plexapi.exceptions.BadRequest:
                await ctx.send(PlexUsername + " is not a valid Plex username.")
        else:
            await ctx.send(
                'Adding ' + PlexUsername + ' to ' + PLEX_SERVER_NAME + '. Please wait about 30 seconds...')
            try:
                added = await self.add_to_plex(PlexUsername, user.id, 's', serverNumber)
                if added:
                    role = discord.utils.get(ctx.message.guild.roles, name=AFTER_APPROVED_ROLE_NAME)
                    await user.add_roles(role, reason="Access membership channels")
                    await ctx.send(
                        user.mention + " You've been invited, " + PlexUsername + ". Welcome to " + PLEX_SERVER_NAME + "!")
                else:
                    await ctx.send(user.name + " could not be added to Plex.")
            except plexapi.exceptions.BadRequest:
                await ctx.send(PlexUsername + " is not a valid Plex username.")

    @pm_add.error
    async def pm_add_error(self, ctx, error):
        print(error)
        await ctx.send("Please mention the Discord user to add to Plex, as well as their Plex username.")

    @pm.command(name="remove", alias=["uninvite", "delete", "rem"])
    @commands.has_role(ADMIN_ROLE_NAME)
    async def pm_remove(self, ctx: commands.Context, user: discord.Member):
        """
        Remove a Discord user from Plex
        """
        deleted, num = self.delete_from_plex(user.id)
        if deleted:
            role = discord.utils.get(ctx.message.guild.roles, name=AFTER_APPROVED_ROLE_NAME)
            await user.remove_roles(role, reason="Removed from Plex")
            await ctx.send("You've been removed from " + (
                PLEX_SERVER_NAME[num] if MULTI_PLEX else PLEX_SERVER_NAME) + ", " + user.mention + ".")
        else:
            await ctx.send("User could not be removed.")

    @pm_remove.error
    async def pm_remove_error(self, ctx, error):
        print(error)
        await ctx.send("Please mention the Discord user to remove from Plex.")

    @pm.command(name="trial")
    @commands.has_role(ADMIN_ROLE_NAME)
    async def pm_trial(self, ctx: commands.Context, user: discord.Member, PlexUsername: str, serverNumber: int = None):
        """
        Start a Plex trial
        """
        if MULTI_PLEX:
            if serverNumber is None:  # No specific number indicated. Defaults adding to the least-fill server
                serverNumber = getSmallestServer()
            elif serverNumber > len(PLEX_SERVER_URL):
                await ctx.send("That server number does not exist.")
            else:
                serverNumber = serverNumber - 1  # user's "server 5" is really server 4 in the index
            await ctx.send('Adding ' + PlexUsername + ' to ' + PLEX_SERVER_NAME[
                serverNumber] + '. Please wait about 30 seconds...')
            try:
                added = await self.add_to_plex(PlexUsername, user.id, 't', serverNumber)
                if added:
                    role = discord.utils.get(ctx.message.guild.roles, name=TRIAL_ROLE_NAME)
                    await user.add_roles(role, reason="Trial started.")
                    await user.create_dm()
                    await user.dm_channel.send(trial_message('start', serverNumber))
                    await ctx.send(
                        user.mention + ", your trial has begun. Please check your Direct Messages for details.")
                else:
                    await ctx.send(user.name + " could not be added to that server.")
            except plexapi.exceptions.BadRequest:
                await ctx.send(PlexUsername + " is not a valid Plex username.")
        else:
            await ctx.send(
                'Starting ' + PLEX_SERVER_NAME + ' trial for ' + PlexUsername + '. Please wait about 30 seconds...')
            try:
                added = await self.add_to_plex(PlexUsername, user.id, 't')
                if added:
                    role = discord.utils.get(ctx.message.guild.roles, name=TRIAL_ROLE_NAME)
                    await user.add_roles(role, reason="Trial started.")
                    await user.create_dm()
                    await user.dm_channel.send(trial_message('start'))
                    await ctx.send(
                        user.mention + ", your trial has begun. Please check your Direct Messages for details.")
                else:
                    await ctx.send(user.name + " could not be added to Plex.")
            except plexapi.exceptions.BadRequest:
                await ctx.send(PlexUsername + " is not a valid Plex username.")

    @pm_trial.error
    async def pm_trial_error(self, ctx, error):
        print(error)
        await ctx.send("Please mention the Discord user to add to Plex, as well as their Plex username.")

    @pm.command(name="import", pass_context=True)
    @commands.has_role(ADMIN_ROLE_NAME)
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
        elif serverNumber is not None and serverNumber > len(PLEX_SERVER_URL):
            await ctx.send("That server number does not exist.")
        else:
            new_entry = db.add_user_to_db(user.id, PlexUsername, subType, serverNumber)
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
    @commands.has_role(ADMIN_ROLE_NAME)
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
        results = db.find_user_in_db("Plex", user.id)
        name = results[0]
        note = results[1]
        num = None
        if MULTI_PLEX:
            num = results[2]
        if name is not None:
            await ctx.send(user.mention + " is Plex user: " + name + (" [Trial" if note == 't' else " [Subscriber") + (
                " - Server " + str(num) if MULTI_PLEX else "") + "]")
        else:
            await ctx.send("User not found.")

    @pm_find.command(name="discord", aliases=["d"])
    @commands.has_role(ADMIN_ROLE_NAME)
    async def pm_find_discord(self, ctx: commands.Context, PlexUsername: str):
        """
        Find Plex user's Discord name
        """
        id = db.find_user_in_db("Discord", PlexUsername)[0]
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
    @commands.has_role(ADMIN_ROLE_NAME)
    async def pm_info_plex(self, ctx, PlexUsername: str):
        """
        Get database entry for Plex username
        """
        embed = discord.Embed(title=("Info for " + str(PlexUsername)))
        n = db.describe_table("users")
        d = db.find_entry_in_db("PlexUsername", PlexUsername)
        if d:
            for i in range(0, len(n)):
                val = str(d[i])
                if str(n[i][1]) == "DiscordID":
                    val = val + " (" + self.bot.get_user(int(d[i])).mention + ")"
                if str(n[i][1]) == "Note":
                    val = ("Trial" if d[i] == 't' else "Subscriber")
                if MULTI_PLEX and str(n[i][1]) == "ServerNum":
                    val = ("Server Number: " + d[i])
                if d[i] is not None:
                    embed.add_field(name=str(n[i][1]), value=val, inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send("That user is not in the database.")

    @pm_info.command(name="discord", aliases=["d"])
    @commands.has_role(ADMIN_ROLE_NAME)
    async def pm_info_discord(self, ctx, user: discord.Member):
        """
        Get database entry for Discord user
        """
        embed = discord.Embed(title=("Info for " + user.name))
        n = db.describe_table("users")
        d = db.find_entry_in_db("DiscordID", user.id)
        if d:
            for i in range(0, len(n)):
                name = str(n[i][1])
                val = str(d[i])
                if str(n[i][1]) == "DiscordID":
                    val = val + " (" + self.bot.get_user(int(d[i])).mention + ")"
                if str(n[i][1]) == "Note":
                    val = ("Trial" if d[i] == 't' else "Subscriber")
                if MULTI_PLEX and str(n[i][1]) == "ServerNum":
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
        if AUTO_WINNERS:
            if message.author.id == GIVEAWAY_BOT_ID and "congratulations" in message.content.lower() and message.mentions:
                tempWinner = discord.utils.get(message.guild.roles, name=TEMP_WINNER_ROLE_NAME)
                for u in message.mentions:
                    await u.add_roles(tempWinner, reason="Winner - access winner invite channel")
            if message.channel.id == WINNER_CHANNEL and discord.utils.get(message.guild.roles,
                                                                          name=TEMP_WINNER_ROLE_NAME) in message.author.roles:
                plexname = message.content.strip()  # Only include username, nothing else
                await message.channel.send(
                    "Adding " + plexname + ". Please wait about 30 seconds...\n"
                                           "Be aware, you will be removed from this channel once you are added "
                                           "successfully.")
                try:
                    serverNumber = None
                    if MULTI_PLEX:
                        serverNumber = getSmallestServer()
                    await self.add_to_plex(plexname, message.author.id, 'w', serverNumber)
                    await message.channel.send(
                        message.author.mention + " You've been invited, " + plexname + ". Welcome to " + PLEX_SERVER_NAME + "!")
                    await message.author.remove_roles(
                        discord.utils.get(message.guild.roles, name=TEMP_WINNER_ROLE_NAME),
                        reason="Winner was processed successfully.")
                except plexapi.exceptions.BadRequest:
                    await message.channel.send(
                        message.author.mention + ", " + plexname + " is not a valid Plex username.")

    @commands.Cog.listener()
    async def on_ready(self):
        self.check_trials.start()
        self.check_subs.start()

    def __init__(self, bot):
        self.bot = bot
        print("Plex Manager ready to go.")
