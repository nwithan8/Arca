"""
Interact with a Jellyfin Media Server, manage users
Copyright (C) 2019 Nathan Harris
"""

import discord
from discord.ext import commands, tasks
import json
import requests
import sqlite3
import os
import random
import string
import csv
import jellyfin.jellyfin_api as jf
from jellyfin.db_commands import DB

# Discord-to-Jellyfin database (SQLite3)
SQLITE_FILE = 'jellyfin/JellyfinDiscord.db'  # File path + name + extension (i.e. "/root/nwithan8-cogs/jellyfin_manager/JellyfinDiscord.db"
'''
Database schema:

JellyfinDiscord.users
(DiscordID BIGINT, JellyfinUsername 'VARCHAR(100)', JellyfinID 'VARCHAR(100)')
'''

JELLYFIN_URL = os.environ.get('JELLYFIN_URL')
JELLYFIN_KEY = os.environ.get('JELLYFIN_KEY')
SERVER_NICKNAME = os.environ.get('JELLYFIN_SERVER_NAME')

# Discord (Admin) settings
SERVER_ID = os.environ.get('DISCORD_SERVER_ID')
ADMIN_ID = os.environ.get('ADMIN_ID')
ADMIN_ROLE_NAME = "Admin"
afterApprovedRoleName = "Invited"
subRoles = ["Monthly Subscriber", "Yearly Subscriber", "Winner", "Bot"]  # Exempt from removal
exemptsubs = [ADMIN_ID]  # Discord IDs for users exempt from subscriber checks/deletion, separated by commas
SUB_CHECK_TIME = 7  # days

# Trial settings
TRIAL_ROLE_NAME = "Trial Member"
TRIAL_LENGTH = 24  # hours
TRIAL_CHECK_FREQUENCY = 15  # minutes
TRIAL_END_NOTIFICATION = "Hello, your " + str(TRIAL_LENGTH) + "-hour trial of " + str(SERVER_NICKNAME) + " has ended."

# Winner settings
WINNER_ROLE_NAME = "Winner"
WINNER_THRESHOLD = 7200  # 2 hours in seconds
AUTO_WINNERS = False
# True: Messages from the indicated GIVEAWAY_BOT_ID user will be scanned for mentioned Discord users (winners). The
# winners will be auto-assigned the TEMP_WINNER_ROLE_NAME. That role gives them access to a specified WINNER_CHANNEL
# channel Users then post their Jellyfin username (ONLY their Jellyfin username) in the channel, which is processed
# by the bot. The bot invites the Jellyfin username, and associates the Discord user author of the message with the
# Jellyfin username in the database. The user is then have the TEMP_WINNER_ROLE_NAME role removed (which removes them
# from the WINNER_CHANNEL channel), and assigned the final WINNER_ROLE_NAME role.
TEMP_WINNER_ROLE_NAME = "Uninvited Winner"
WINNER_CHANNEL = 0  # Channel ID
GIVEAWAY_BOT_ID = 0

# Credentials settings
CREATE_PASSWORD = True
NO_PASSWORD_MESSAGE = "Leave password blank on first login, but please secure your account by setting a password."
USE_HASTEBIN = False
HASTEBIN_URL = 'https://hastebin.com'

# Migrate/mass import users
MIGRATION_FILE = "/"  # file path + name (leave off ".csv" extension)

# DO NOT EDIT
db = DB(SQLITE_FILE, TRIAL_LENGTH)


def password(length):
    """
    Generate a random string of letters and digits
    """
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))


def add_password(uid):
    p = password(length=10)
    r = jf.resetPassword(uid)
    if str(r.status_code).startswith('2'):
        r = jf.setUserPassword(uid, "", p)
        if str(r.status_code).startswith('2'):
            return p
    return None


def update_policy(uid, policy=None):
    if str(jf.updatePolicy(uid, policy).status_code).startswith('2'):
        return True
    return False


def hastebin(content, url=HASTEBIN_URL):
    post = requests.post(f'{url}/documents', data=content.encode('utf-8'))
    return '{}/{}'.format(url, post.json()['key'])


async def sendAddMessage(user, username, pwd=None):
    if USE_HASTEBIN:
        creds = hastebin(
            "Hostname: {}\nUsername: {}\n{}\n".format(str(JELLYFIN_URL), str(username), (
                "Password: " + pwd if CREATE_PASSWORD else NO_PASSWORD_MESSAGE)))
    else:
        creds = "Hostname: {}\nUsername: {}\n{}\n".format(str(JELLYFIN_URL), str(username), (
            "Password: " + pwd if CREATE_PASSWORD else NO_PASSWORD_MESSAGE))
    await user.create_dm()
    await user.dm_channel.send("You have been added to {}!\n{}".format(
        str(SERVER_NICKNAME), creds))


def get_jellyfin_users():
    """
    Return dictionary {'user_name': 'user_id'}
    """
    users = {}
    for u in jf.getUsers():
        users[u['name']] = u['id']
    return users


def add_to_jellyfin(username, discordId, note):
    """
    Add a Discord user to Jellyfin

    :returns ('policyMade': True/False, 'userId': str(id)/str(failure reason), 'password': str/None)
    """
    try:
        p = None
        r = jf.makeUser(username)
        if str(r.status_code).startswith('2'):
            uid = json.loads(r.text)['Id']
            p = add_password(uid)
            policyEnforced = False
            if not p:
                print("Password update for {} failed. Moving on...".format(username))
            success = db.add_user_to_db(discordId, username, uid, note)
            if success:
                POLICY = {
                    "IsAdministrator": "false",
                    "IsHidden": "true",
                    "IsHiddenRemotely": "true",
                    "IsDisabled": "false",
                    "EnableRemoteControlOfOtherUsers": "false",
                    "EnableSharedDeviceControl": "false",
                    "EnableRemoteAccess": "true",
                    "EnableLiveTvManagement": "false",
                    "EnableLiveTvAccess": "false",
                    "EnableContentDeletion": "false",
                    "EnableContentDownloading": "false",
                    "EnableSyncTranscoding": "false",
                    "EnableSubtitleManagement": "false",
                    "EnableAllDevices": "true",
                    "EnableAllChannels": "false",
                    "EnablePublicSharing": "false",
                    "InvalidLoginAttemptCount": 5,
                    "BlockedChannels": [
                        "IPTV",
                        "TVHeadEnd Recordings"
                    ]
                }
                if update_policy(uid, POLICY):
                    policyEnforced = True
            return policyEnforced, uid, p
        return False, r.content.decode("utf-8"), p
    except Exception as e:
        print(e)
        return False, None, None


def remove_from_jellyfin(id):
    """
    Remove a Discord user from Jellyfin
    Returns:
    200 - user found and removed successfully
    600 - user found, but not removed
    700 - user not found in database
    500 - unknown error
    """
    try:
        jellyfinId = db.find_user_in_db("Jellyfin", id)
        if not jellyfinId:
            return 700  # user not found
        disable_policy = {
            "IsAdministrator": "false",
            "IsHidden": "true",
            "IsHiddenRemotely": "true",
            "IsDisabled": "true",
            "EnableRemoteControlOfOtherUsers": "false",
            "EnableSharedDeviceControl": "false",
            "EnableRemoteAccess": "true",
            "EnableLiveTvManagement": "false",
            "EnableLiveTvAccess": "false",
            "EnableContentDeletion": "false",
            "EnableSubtitleManagement": "false",
            "EnableAllDevices": "true",
            "EnableAllChannels": "false",
            "EnablePublicSharing": "false",
            "BlockedChannels": [
                "IPTV",
                "TVHeadEnd Recordings"
            ]
        }
        r = jf.deleteUser(jellyfinId)
        if not str(r.status_code).startswith('2'):
            return 600  # user not deleted
        db.remove_user_from_db(id)
        return 200  # user removed successfully
    except Exception as e:
        print(e)
        return 500  # unknown error


def remove_nonsub(memberID):
    if memberID not in exemptsubs:
        remove_from_jellyfin(memberID)


class Jellyfin(commands.Cog):

    async def purge_winners(self, ctx):
        try:
            winners = db.getWinners()
            monitorlist = []
            for u in winners:
                monitorlist.append(u[0])
            print("Winners: ")
            print(monitorlist)
            removed_list = ""
            error_message = ""
            for u in monitorlist:
                try:
                    query = {
                        "CustomQueryString": "SELECT SUM(PlayDuration) FROM PlaybackActivity WHERE UserId = '{}' AND "
                                             "DateCreated >= date(julianday(date('now'))-14)".format(str(u)),
                        "ReplaceUserId": "false"}
                    # returns time watched in last 14 days, in seconds
                    watchtime = jf.statsCustomQuery(query)['results'][0][0]
                    if not watchtime:
                        watchtime = 0
                    watchtime = int(watchtime)
                    if watchtime < WINNER_THRESHOLD:
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
            id = db.find_user_in_db("Discord", jellyfinId)
            if id is not None:
                code = remove_from_jellyfin(jellyfinId)
                if code.startswith('2'):
                    user = self.bot.get_user(int(id))
                    await user.create_dm()
                    await user.dm_channel.send(
                        "You have been removed from {} due to inactivity.".format(str(SERVER_NICKNAME)))
                    await user.remove_roles(discord.utils.get(self.bot.get_guild(int(SERVER_ID)).roles, name="Winner"),
                                            reason="Inactive winner")
                    return "<@{}>, ".format(id)
        except Exception as e:
            pass
        return None

    @tasks.loop(seconds=SUB_CHECK_TIME * (3600 * 24))
    async def check_subs(self):
        print("Checking Jellyfin subs...")
        exemptRoles = []
        allRoles = self.bot.get_guild(int(SERVER_ID)).roles
        for r in allRoles:
            if r.name in subRoles:
                exemptRoles.append(r)
        for member in self.bot.get_guild(int(SERVER_ID)).members:
            if not any(x in member.roles for x in exemptRoles):
                remove_nonsub(member.id)
        print("Jellyfin Subs check completed.")

    @tasks.loop(seconds=TRIAL_CHECK_FREQUENCY * 60)
    async def check_trials(self):
        print("Checking Jellyfin trials...")
        trials = db.getTrials()
        trial_role = discord.utils.get(self.bot.get_guild(int(SERVER_ID)).roles, name=TRIAL_ROLE_NAME)
        for u in trials:
            print("Ending trial for {}".format(str(u[0])))
            remove_from_jellyfin(int(u[0]))
            try:
                user = self.bot.get_guild(int(SERVER_ID)).get_member(int(u[0]))
                await user.create_dm()
                await user.dm_channel.send(TRIAL_END_NOTIFICATION)
                await user.remove_roles(trial_role, reason="Trial has ended.")
            except Exception as e:
                print(e)
                print("Discord user {} not found.".format(str(u[0])))
        print("Jellyfin Trials check completed.")

    @commands.group(aliases=["Jellyfin", "jf", "JF"], pass_context=True)
    async def jellyfin(self, ctx: commands.Context):
        """
        Jellyfin Media Server commands
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")

    @jellyfin.command(name="access", pass_context=True)
    # Anyone can use this command
    async def jellyfin_access(self, ctx: commands.Context, JellyfinUsername: str = None):
        """
        Check if you or another user has access to the Jellyfin server
        """
        if JellyfinUsername is None:
            name, note = db.find_username_in_db("Jellyfin", ctx.message.author.id)
        else:
            name = JellyfinUsername
        if name in get_jellyfin_users().keys():
            await ctx.send(
                '{} access to {}'.format(("You have" if JellyfinUsername is None else name + " has"), SERVER_NICKNAME))
        else:
            await ctx.send('{} not have access to {}'.format(("You do" if JellyfinUsername is None else name + " does"),
                                                             SERVER_NICKNAME))

    @jellyfin_access.error
    async def jellyfin_access_error(self, ctx, error):
        print(error)
        await ctx.send("Sorry, something went wrong.")

    @jellyfin.command(name="status", aliases=['ping', 'up', 'online'], pass_context=True)
    # Anyone can use this command
    async def jellyfin_status(self, ctx: commands.Context):
        """
        Check if the Jellyfin server is online
        """
        r = requests.get(JELLYFIN_URL + "/swagger", timeout=10)
        if r.status_code != 200:
            await ctx.send(SERVER_NICKNAME + " is having connection issues right now.")
        else:
            await ctx.send(SERVER_NICKNAME + " is up and running.")

    @jellyfin_status.error
    async def jellyfin_status_error(self, ctx, error):
        print(error)
        await ctx.send("Sorry, I couldn't test the connection.")

    @jellyfin.command(name="winners", pass_context=True)
    @commands.has_role(ADMIN_ROLE_NAME)
    async def jellyfin_winners(self, ctx: commands.Context):
        """
        List winners' Jellyfin usernames
        """
        conn = sqlite3.connect(SQLITE_FILE)
        try:
            response = "Winners:"
            cur = conn.cursor()
            cur.execute("SELECT JellyfinUsername FROM users WHERE Note = 'w'")
            for u in cur.fetchall():
                response = response + "\n" + (u[0])
            await ctx.send(response)
        except Exception as e:
            await ctx.send("Error pulling winners from database.")

    @jellyfin.command(name="purge", pass_context=True)
    @commands.has_role(ADMIN_ROLE_NAME)
    async def jellyfin_purge(self, ctx: commands.Context):
        """
        Remove inactive winners
        """
        await ctx.send("Purging winners...")
        await self.purge_winners(ctx)

    @jellyfin.command(name="cleandb", aliases=['clean', 'scrub', 'syncdb'], pass_context=True)
    @commands.has_role(ADMIN_ROLE_NAME)
    async def jellyfin_cleandb(self, ctx: commands.Context):
        """
        Remove old users from database
        If you delete a user from Jellyfin directly,
        run this to remove the user's entry in the
        Jellyfin user database.
        """
        existingUsers = get_jellyfin_users()
        dbEntries = db.get_all_entries_in_db()
        if dbEntries:
            deletedUsers = ""
            for entry in dbEntries:
                if entry[1] not in existingUsers.keys():  # entry[1] is JellyfinUsername
                    deletedUsers += entry[1] + ", "
                    db.remove_user_from_db(entry[0])  # entry[0] is DiscordID
            if deletedUsers:
                await ctx.send("The following users were deleted from the database: " + deletedUsers[:-2])
            else:
                await ctx.send("No old users found and removed from database.")
        else:
            await ctx.send("An error occurred when grabbing users from the database.")

    @jellyfin_cleandb.error
    async def jellyfin_cleandb_error(self, ctx, error):
        print(error)
        await ctx.send("Something went wrong.")

    @jellyfin.command(name="count", aliases=["subs", "number"], pass_context=True)
    @commands.has_role(ADMIN_ROLE_NAME)
    async def jellyfin_count(self, ctx: commands.Context):
        """
        Get the number of enabled Jellyfin users
        """
        count = len(get_jellyfin_users())
        if count > 0:
            await ctx.send(str(SERVER_NICKNAME) + " has " + str(count) + " users.")
        else:
            await ctx.send("An error occurred.")

    @jellyfin_count.error
    async def jellyfin_count_error(self, ctx, error):
        print(error)
        await ctx.send("Something went wrong. Please try again later.")

    @jellyfin.command(name="add", aliases=["new", "join"], pass_context=True)
    @commands.has_role(ADMIN_ROLE_NAME)
    async def jellyfin_add(self, ctx: commands.Context, user: discord.Member, username: str):
        """
        Add a Discord user to Jellyfin
        """
        s, u, p = add_to_jellyfin(username, user.id, 's')
        if s:
            await sendAddMessage(user, username, (p if CREATE_PASSWORD else NO_PASSWORD_MESSAGE))
            await ctx.send(
                "You've been added, {}! Please check your direct messages for login information.".format(user.mention))
        else:
            await ctx.send("An error occurred while adding {}".format(user.mention))

    @jellyfin_add.error
    async def jellyfin_add_error(self, ctx, error):
        print(error)
        await ctx.send("Please mention the Discord user to add to Jellyfin, as well as their Jellyfin username.")

    @jellyfin.command(name="remove", aliases=["delete", "rem"], pass_context=True)
    @commands.has_role(ADMIN_ROLE_NAME)
    async def jellyfin_remove(self, ctx: commands.Context, user: discord.Member):
        """
        Delete a Discord user from Jellyfin
        """
        s = remove_from_jellyfin(user.id)
        if s == 200:
            await ctx.send("You've been removed from " + str(SERVER_NICKNAME) + ", " + user.mention + ".")
        elif s == 600:
            await ctx.send(user.mention + " could not be removed.")
        elif s == 700:
            await ctx.send("There are no accounts for " + user.mention)
        else:
            await ctx.send("An error occurred while removing " + user.mention)

    @jellyfin_remove.error
    async def jellyfin_remove_error(self, ctx, error):
        print(error)
        await ctx.send("Please mention the Discord user to remove from Jellyfin.")

    @jellyfin.command(name="trial", pass_context=True)
    @commands.has_role(ADMIN_ROLE_NAME)
    async def jellyfin_trial(self, ctx: commands.Context, user: discord.Member, JellyfinUsername: str):
        """
        Start a trial of Jellyfin
        """
        s, u, p = add_to_jellyfin(JellyfinUsername, user.id, 't')
        if s:
            await sendAddMessage(user, JellyfinUsername, (p if CREATE_PASSWORD else NO_PASSWORD_MESSAGE))
        else:
            await ctx.send("An error occurred while starting a trial for {}".format(user.mention))

    @jellyfin_trial.error
    async def jellyfin_trial_error(self, ctx, error):
        print(error)
        await ctx.send("Please mention the Discord user to add to Jellyfin, as well as their Jellyfin username.")

    @jellyfin.command(name="import", pass_context=True)
    @commands.has_role(ADMIN_ROLE_NAME)
    async def jellyfin_import(self, ctx: commands.Context, user: discord.Member, JellyfinUsername: str, subType: str,
                              serverNumber: int = None):
        """
        Add existing Jellyfin users to the database.
        user - tag a Discord user
        JellyfinUsername - Jellyfin username of the Discord user
        subType - custom note for tracking subscriber type; MUST be less than 5 letters.
        Default in database: 's' for Subscriber, 'w' for Winner, 't' for Trial.
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
                new_entry = db.add_user_to_db(user.id, JellyfinUsername, jellyfinId, subType)
                if new_entry:
                    if subType == 't':
                        await ctx.send("Trial user was added/new timestamp issued.")
                    else:
                        await ctx.send("User added to the database.")
                else:
                    await ctx.send("User already exists in the database.")

    @jellyfin_import.error
    async def jellyfin_import_error(self, ctx, error):
        print(error)
        await ctx.send(
            "Please mention the Discord user to add to the database, including their Jellyfin username and sub type.")

    @jellyfin.group(name="find", aliases=["id"], pass_context=True)
    @commands.has_role(ADMIN_ROLE_NAME)
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
        name, note = db.find_username_in_db("Jellyfin", user.id)
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
        id, note = db.find_username_in_db("Discord", JellyfinUsername)
        if id:
            await ctx.send('{} is Discord user: {}'.format(JellyfinUsername, self.bot.get_user(int(id)).mention))
        else:
            await ctx.send("User not found.")

    @jellyfin_find.error
    async def jellyfin_find_error(self, ctx, error):
        await ctx.send("An error occurred while looking for that user.")
        print(error)

    @jellyfin.group(name="info")
    @commands.has_role(ADMIN_ROLE_NAME)
    async def jellyfin_info(self, ctx: commands.Context):
        """
        Get database entry for a user
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")

    @jellyfin_info.command(name="jellyfin", aliases=["j"])
    async def jellyfin_info_jellyfin(self, ctx, JellyfinUsername: str):
        """
        Get database entry for Jellyfin username
        """
        embed = discord.Embed(title=("Info for {}".format(str(JellyfinUsername))))
        n = db.describe_table("users")
        d = db.find_entry_in_db("JellyfinUsername", JellyfinUsername)
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
            await ctx.send("That user is not in the database.")

    @jellyfin_info.command(name="discord", aliases=["d"])
    async def jellyfin_info_discord(self, ctx, user: discord.Member):
        """
        Get database entry for Discord user
        """
        embed = discord.Embed(title=("Info for {}".format(user.name)))
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
                if d[i] is not None:
                    embed.add_field(name=str(n[i][1]), value=val, inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send("That user is not in the database.")

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
        with open(MIGRATION_FILE + '.csv', mode='r') as f:
            reader = csv.DictReader(f)
            writer = csv.writer(f)
            for row in reader:
                jellyfin_username = row['Discord_Tag'].split("#")[0]  # Jellyfin username will be Discord username
                user = discord.utils.get(ctx.message.guild.members, name=jellyfin_username)
                s, u, p = add_to_jellyfin(jellyfin_username, user.id, 's')  # Users added as 'Subscribers'
                if s:
                    await sendAddMessage(user, jellyfin_username, (p if CREATE_PASSWORD else NO_PASSWORD_MESSAGE))
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
        if AUTO_WINNERS:
            if message.author.id == GIVEAWAY_BOT_ID and "congratulations" in message.content.lower() and message.mentions:
                tempWinner = discord.utils.get(message.guild.roles, name=TEMP_WINNER_ROLE_NAME)
                for u in message.mentions:
                    await u.add_roles(tempWinner, reason="Winner - access winner invite channel")
            if message.channel.id == WINNER_CHANNEL and discord.utils.get(message.guild.roles,
                                                                          name=TEMP_WINNER_ROLE_NAME) in message.author.roles:
                username = message.content.strip()  # Only include username, nothing else
                s, u, p = add_to_jellyfin(username, message.author.id, 'w')
                if s:
                    await sendAddMessage(message.author, username, (p if CREATE_PASSWORD else NO_PASSWORD_MESSAGE))
                    await message.channel.send(
                        "You've been added, {}! Please check your direct messages for login information.".format(
                            message.author.mention))
                    await message.author.remove_roles(
                        discord.utils.get(message.guild.roles, name=TEMP_WINNER_ROLE_NAME),
                        reason="Winner was processed successfully.")
                else:
                    if "exist" in s:
                        await message.channel.send(s)
                    else:
                        await message.channel.send("An error occurred while adding {}".format(message.author.mention))

    @commands.Cog.listener()
    async def on_ready(self):
        self.check_trials.start()
        self.check_subs.start()
        pass

    def __init__(self, bot):
        self.bot = bot
        jf.authenticate()
        print("Jellyfin Manager ready to go.")
