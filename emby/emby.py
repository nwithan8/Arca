"""
Interact with a Emby Media Server, manage users
Copyright (C) 2019 Nathan Harris
"""

import discord
from discord.ext import commands, tasks
import json
import sqlite3
import random
import string
import csv
import emby.settings as settings
import emby.emby_api as em
from emby.db_commands import DB
from helper.pastebin import hastebin, privatebin

db = DB(settings.SQLITE_FILE, (settings.TRIAL_LENGTH * 3600))


def password(length):
    """
    Generate a random string of letters and digits
    """
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))


def add_password(uid):
    p = password(length=10)
    r = em.resetPassword(uid)
    if str(r.status_code).startswith('2'):
        r = em.setUserPassword(uid, "", p)
        if str(r.status_code).startswith('2'):
            return p
    return None


def update_policy(uid, policy=None):
    if str(em.updatePolicy(uid, policy).status_code).startswith('2'):
        return True
    return False


async def sendAddMessage(user, username, pwd=None):
    text = "Hostname: {}\nUsername: {}\n{}\n".format(str(settings.EMBY_URL), str(username), (
        "Password: " + pwd if settings.CREATE_PASSWORD else settings.NO_PASSWORD_MESSAGE))
    if settings.USE_PASTEBIN:
        if settings.USE_PASTEBIN == 'privatebin':
            data, error = privatebin(
                text=text,
                url=settings.PRIVATEBIN_URL,
                pass_protect=False,
                expiration='1week',
                burn_after_reading=False
            )
        if settings.USE_PASTEBIN == 'hastebin':
            data, error = hastebin(
                text=text,
                url=settings.HASTEBIN_URL
            )
        if not error:
            text = data['url']
        else:
            print("Error uploading to pastebin: {}".format(error))
    await user.create_dm()
    await user.dm_channel.send("You have been added to {}!\n{}".format(
        str(settings.EMBY_SERVER_NICKNAME), text))


def get_emby_users():
    """
    Return dictionary {'user_name': 'user_id'}
    """
    users = {}
    for u in em.getUsers():
        users[u['name']] = u['id']
    return users


async def add_to_emby(username, discordId, note, useEmbyConnect=False):
    """
    Add a Discord user to Emby

    :returns ('policyMade': True/False, 'userId': str(id)/str(failure reason), 'password': str/None)
    """
    try:
        p = None
        r = em.makeUser(username)
        if str(r.status_code).startswith('2'):
            uid = json.loads(r.text)['Id']
            p = add_password(uid)
            policyEnforced = False
            if not p:
                print("Password update for {} failed. Moving on...".format(username))
            if useEmbyConnect:
                await em.addConnectUser(connect_username=username, user_id=uid)
            success = db.add_user_to_db(discordId, username, uid, note)
            if success:
                if update_policy(uid, settings.EMBY_USER_POLICY):
                    policyEnforced = True
            return policyEnforced, uid, p
        return False, r.content.decode("utf-8"), p
    except Exception as e:
        print(e)
        return False, None, None


def remove_from_emby(id):
    """
    Remove a Discord user from Emby
    Returns:
    200 - user found and removed successfully
    600 - user found, but not removed
    700 - user not found in database
    500 - unknown error
    """
    try:
        embyId = db.find_user_in_db("Emby", id)
        if not embyId:
            return 700  # user not found
        r = em.deleteUser(embyId)
        if not str(r.status_code).startswith('2'):
            return 600  # user not deleted
        db.remove_user_from_db(id)
        return 200  # user removed successfully
    except Exception as e:
        print(e)
        return 500  # unknown error


def remove_nonsub(memberID):
    if memberID not in settings.EXEMPT_SUBS:
        remove_from_emby(memberID)


class Emby(commands.Cog):

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
                    watchtime = em.statsCustomQuery(query)['results'][0][0]
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

    async def remove_winner(self, embyId):
        try:
            id = db.find_user_in_db("Discord", embyId)
            if id is not None:
                code = remove_from_emby(embyId)
                if code.startswith('2'):
                    user = self.bot.get_user(int(id))
                    await user.create_dm()
                    await user.dm_channel.send(
                        "You have been removed from {} due to inactivity.".format(str(settings.EMBY_SERVER_NICKNAME)))
                    await user.remove_roles(discord.utils.get(self.bot.get_guild(int(settings.DISCORD_SERVER_ID)).roles,
                                                              name=settings.WINNER_ROLE_NAME),
                                            reason="Inactive winner")
                    return "<@{}>, ".format(id)
        except Exception as e:
            pass
        return None

    @tasks.loop(seconds=settings.SUB_CHECK_TIME * (3600 * 24))
    async def check_subs(self):
        print("Checking Emby subs...")
        exemptRoles = []
        allRoles = self.bot.get_guild(int(settings.DISCORD_SERVER_ID)).roles
        for r in allRoles:
            if r.name in settings.SUB_ROLES:
                exemptRoles.append(r)
        for member in self.bot.get_guild(int(settings.DISCORD_SERVER_ID)).members:
            if not any(x in member.roles for x in exemptRoles):
                remove_nonsub(member.id)
        print("Emby Subs check completed.")

    @tasks.loop(seconds=settings.TRIAL_CHECK_FREQUENCY * 60)
    async def check_trials(self):
        print("Checking Emby trials...")
        trials = db.getTrials()
        trial_role = discord.utils.get(self.bot.get_guild(int(settings.DISCORD_SERVER_ID)).roles,
                                       name=settings.TRIAL_ROLE_NAME)
        for u in trials:
            print("Ending trial for {}".format(str(u[0])))
            remove_from_emby(int(u[0]))
            try:
                user = self.bot.get_guild(int(settings.DISCORD_SERVER_ID)).get_member(int(u[0]))
                await user.create_dm()
                await user.dm_channel.send(settings.TRIAL_END_NOTIFICATION)
                await user.remove_roles(trial_role, reason="Trial has ended.")
            except Exception as e:
                print(e)
                print("Discord user {} not found.".format(str(u[0])))
        print("Emby Trials check completed.")

    @commands.group(aliases=["Emby", "em", "JF"], pass_context=True)
    async def emby(self, ctx: commands.Context):
        """
        Emby Media Server commands
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")

    @emby.command(name="access", pass_context=True)
    # Anyone can use this command
    async def emby_access(self, ctx: commands.Context, EmbyUsername: str = None):
        """
        Check if you or another user has access to the Emby server
        """
        if EmbyUsername is None:
            name, note = db.find_username_in_db("Emby", ctx.message.author.id)
        else:
            name = EmbyUsername
        if name in get_emby_users().keys():
            await ctx.send(
                '{} access to {}'.format(("You have" if EmbyUsername is None else name + " has"),
                                         settings.EMBY_SERVER_NICKNAME))
        else:
            await ctx.send('{} not have access to {}'.format(("You do" if EmbyUsername is None else name + " does"),
                                                             settings.EMBY_SERVER_NICKNAME))

    @emby_access.error
    async def emby_access_error(self, ctx, error):
        print(error)
        await ctx.send("Sorry, something went wrong.")

    @emby.command(name="status", aliases=['ping', 'up', 'online'], pass_context=True)
    # Anyone can use this command
    async def emby_status(self, ctx: commands.Context):
        """
        Check if the Emby server is online
        """
        if em.getStatus() != 200:
            await ctx.send(settings.EMBY_SERVER_NICKNAME + " is having connection issues right now.")
        else:
            await ctx.send(settings.EMBY_SERVER_NICKNAME + " is up and running.")

    @emby_status.error
    async def emby_status_error(self, ctx, error):
        print(error)
        await ctx.send("Sorry, I couldn't test the connection.")

    @emby.command(name="winners", pass_context=True)
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def emby_winners(self, ctx: commands.Context):
        """
        List winners' Emby usernames
        """
        try:
            winners = db.getWinners()
            response = '\n'.join([u[0] for u in winners])
            await ctx.send(response)
        except Exception as e:
            await ctx.send("Error pulling winners from database.")

    @emby.command(name="purge", pass_context=True)
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def emby_purge(self, ctx: commands.Context):
        """
        Remove inactive winners
        """
        await ctx.send("Purging winners...")
        await self.purge_winners(ctx)

    @emby.command(name="cleandb", aliases=['clean', 'scrub', 'syncdb'], pass_context=True)
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def emby_cleandb(self, ctx: commands.Context):
        """
        Remove old users from database
        If you delete a user from Emby directly,
        run this to remove the user's entry in the
        Emby user database.
        """
        existingUsers = get_emby_users()
        dbEntries = db.get_all_entries_in_db()
        if dbEntries:
            deletedUsers = ""
            for entry in dbEntries:
                if entry[1] not in existingUsers.keys():  # entry[1] is EmbyUsername
                    deletedUsers += entry[1] + ", "
                    db.remove_user_from_db(entry[0])  # entry[0] is DiscordID
            if deletedUsers:
                await ctx.send("The following users were deleted from the database: " + deletedUsers[:-2])
            else:
                await ctx.send("No old users found and removed from database.")
        else:
            await ctx.send("An error occurred when grabbing users from the database.")

    @emby_cleandb.error
    async def emby_cleandb_error(self, ctx, error):
        print(error)
        await ctx.send("Something went wrong.")

    @emby.command(name="count", aliases=["subs", "number"], pass_context=True)
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def emby_count(self, ctx: commands.Context):
        """
        Get the number of enabled Emby users
        """
        count = len(get_emby_users())
        if count > 0:
            await ctx.send(str(settings.EMBY_SERVER_NICKNAME) + " has " + str(count) + " users.")
        else:
            await ctx.send("An error occurred.")

    @emby_count.error
    async def emby_count_error(self, ctx, error):
        print(error)
        await ctx.send("Something went wrong. Please try again later.")

    @emby.command(name="add", aliases=["new", "join"], pass_context=True)
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def emby_add(self, ctx: commands.Context, user: discord.Member, username: str, useEmbyConnect: str = False):
        """
        Add a Discord user to Emby
        """
        # s, u, p = add_to_emby(username, user.id, 's', useEmbyConnect=(True if useEmbyConnect else False))
        s, u, p = await add_to_emby(username, user.id, 's', useEmbyConnect=False)
        if s:
            await sendAddMessage(user, username, (p if settings.CREATE_PASSWORD else settings.NO_PASSWORD_MESSAGE))
            await ctx.send(
                "You've been added, {}! Please check your direct messages for login information.".format(user.mention))
        else:
            await ctx.send("An error occurred while adding {}".format(user.mention))

    @emby_add.error
    async def emby_add_error(self, ctx, error):
        print(error)
        await ctx.send("Please mention the Discord user to add to Emby, as well as their Emby username.")

    @emby.command(name="connect", pass_context=True)
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def emby_connect(self, ctx: commands.Context, user: discord.Member, embyConnectUsername: str):
        """
        Connect a local Emby user to an Emby Connect user
        """
        user_id = db.find_user_in_db("Emby", user.id)
        if user_id:
            res = await em.addConnectUser(embyConnectUsername, user_id)
            if str(res.status_code).startswith('2'):
                await ctx.send("The local account for {} has been successfully linked to {}".format(user.mention,
                                                                                                    embyConnectUsername))
            else:
                await ctx.send("Linking failed.")
        else:
            await ctx.send("I couldn't find that user")

    @emby_connect.error
    async def emby_connect_error(self, ctx, error):
        print(error)
        await ctx.send("Please mention the Discord user and their Emby Connect username to link the accounts.")

    @emby.command(name="remove", aliases=["delete", "rem"], pass_context=True)
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def emby_remove(self, ctx: commands.Context, user: discord.Member):
        """
        Delete a Discord user from Emby
        """
        s = remove_from_emby(user.id)
        if s == 200:
            await ctx.send("You've been removed from {}, {}.".format(settings.EMBY_SERVER_NICKNAME, user.mention))
        elif s == 600:
            await ctx.send("{} could not be removed.".format(user.mention))
        elif s == 700:
            await ctx.send("There are no accounts for {}".format(user.mention))
        else:
            await ctx.send("An error occurred while removing {}".format(user.mention))

    @emby_remove.error
    async def emby_remove_error(self, ctx, error):
        print(error)
        await ctx.send("Please mention the Discord user to remove from Emby.")

    @emby.command(name="trial", pass_context=True)
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def emby_trial(self, ctx: commands.Context, user: discord.Member, EmbyUsername: str):
        """
        Start a trial of Emby
        """
        s, u, p = add_to_emby(EmbyUsername, user.id, 't')
        if s:
            await sendAddMessage(user, EmbyUsername, (p if settings.CREATE_PASSWORD else settings.NO_PASSWORD_MESSAGE))
        else:
            await ctx.send("An error occurred while starting a trial for {}".format(user.mention))

    @emby_trial.error
    async def emby_trial_error(self, ctx, error):
        print(error)
        await ctx.send("Please mention the Discord user to add to Emby, as well as their Emby username.")

    @emby.command(name="import", pass_context=True)
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def emby_import(self, ctx: commands.Context, user: discord.Member, EmbyUsername: str, subType: str,
                          serverNumber: int = None):
        """
        Add existing Emby users to the database.
        user - tag a Discord user
        EmbyUsername - Emby username of the Discord user
        subType - custom note for tracking subscriber type; MUST be less than 5 letters.
        Default in database: 's' for Subscriber, 'w' for Winner, 't' for Trial.
        NOTE: subType 't' will make a new 24-hour timestamp for the user.
        """
        users = get_emby_users()
        if EmbyUsername not in users.keys():
            await ctx.send("Not an existing Emby user.")
        else:
            embyId = users[EmbyUsername]
            if len(subType) > 4:
                await ctx.send("subType must be less than 5 characters long.")
            else:
                new_entry = db.add_user_to_db(user.id, EmbyUsername, embyId, subType)
                if new_entry:
                    if subType == 't':
                        await ctx.send("Trial user was added/new timestamp issued.")
                    else:
                        await ctx.send("User added to the database.")
                else:
                    await ctx.send("User already exists in the database.")

    @emby_import.error
    async def emby_import_error(self, ctx, error):
        print(error)
        await ctx.send(
            "Please mention the Discord user to add to the database, including their Emby username and sub type.")

    @emby.group(name="find", aliases=["id"], pass_context=True)
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def emby_find(self, ctx: commands.Context):
        """
        Find Discord or Emby user
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")

    @emby_find.command(name="emby", aliases=["e"])
    async def emby_find_emby(self, ctx: commands.Context, user: discord.Member):
        """
        Find Discord member's Emby username
        """
        name, note = db.find_username_in_db("Emby", user.id)
        if name:
            await ctx.send('{} is Emby user: {}{}'.format(user.mention, name,
                                                          (" [Trial]" if note == 't' else " [Subscriber]")))
        else:
            await ctx.send("User not found.")

    @emby_find.command(name="discord", aliases=["d"])
    async def emby_find_discord(self, ctx: commands.Context, EmbyUsername: str):
        """
        Find Emby user's Discord name
        """
        id, note = db.find_username_in_db("Discord", EmbyUsername)
        if id:
            await ctx.send('{} is Discord user: {}'.format(EmbyUsername, self.bot.get_user(int(id)).mention))
        else:
            await ctx.send("User not found.")

    @emby_find.error
    async def emby_find_error(self, ctx, error):
        await ctx.send("An error occurred while looking for that user.")
        print(error)

    @emby.group(name="info")
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def emby_info(self, ctx: commands.Context):
        """
        Get database entry for a user
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")

    @emby_info.command(name="emby", aliases=["j"])
    async def emby_info_emby(self, ctx, EmbyUsername: str):
        """
        Get database entry for Emby username
        """
        embed = discord.Embed(title=("Info for {}".format(str(EmbyUsername))))
        n = db.describe_table("users")
        d = db.find_entry_in_db("EmbyUsername", EmbyUsername)
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

    @emby_info.command(name="discord", aliases=["d"])
    async def emby_info_discord(self, ctx, user: discord.Member):
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

    @emby_info.error
    async def emby_info_error(self, ctx, error):
        print(error)
        await ctx.send("User not found.")

    @emby.command(name="migrate", pass_context=True)
    async def emby_migrate(self, ctx: commands.Context):
        """
        Migrate Plex users to Emby (using a CSV file)
        File format: Discord_Tag | Plex_Username | Emby_Username
        """
        users = {}
        count = 0
        failed = []
        with open(settings.MIGRATION_FILE + '.csv', mode='r') as f:
            reader = csv.DictReader(f)
            writer = csv.writer(f)
            for row in reader:
                emby_username = row['Discord_Tag'].split("#")[0]  # Emby username will be Discord username
                user = discord.utils.get(ctx.message.guild.members, name=emby_username)
                s, u, p = add_to_emby(emby_username, user.id, 's')  # Users added as 'Subscribers'
                if s:
                    await sendAddMessage(user, emby_username,
                                         (p if settings.CREATE_PASSWORD else settings.NO_PASSWORD_MESSAGE))
                    data = [str(row['Discord_Tag']), str(row['Plex_Username']), str(emby_username)]
                    writer.writerow(data)
                    count += 1
                else:
                    failed.append(emby_username)
            f.close()
        await ctx.send("{} users added to Emby.{}".format(str(count), (
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
                s, u, p = add_to_emby(username, message.author.id, 'w')
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
                    if "exist" in s:
                        await message.channel.send(s)
                    else:
                        await message.channel.send("An error occurred while adding {}".format(message.author.mention))

    @commands.Cog.listener()
    async def on_ready(self):
        #self.check_trials.start()
        #self.check_subs.start()
        pass

    def __init__(self, bot):
        self.bot = bot
        em.authenticate()
        print("Emby Manager ready to go.")
