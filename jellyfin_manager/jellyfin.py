"""
Interact with a Jellyfin Media Server, manage users
Copyright (C) 2019 Nathan Harris
"""

import discord
from discord.ext import commands, tasks
from discord.utils import get
from collections import defaultdict
import random
from imdbpie import Imdb
from imdbpie import ImdbFacade
import re
import json
import requests
#from progress.bar import Bar
#import mysql.connector
import sqlite3
import os
import datetime
from decimal import *
import math
import asyncio
import random
import string
import time
import csv


# Discord-to-Jellyfin database credentials (MySQL)
# DEPRECIATED
#USE_MYSQL = False
#dbhostname = os.environ.get('DATABASE_HOST')
#dbport = os.environ.get('DATABASE_PORT')
#dbusername = os.environ.get('DATABASE_USER')
#dbpassword = os.environ.get('DATABASE_PASS')
#database = 'JellyfinDiscord'

# Discord-to-Jellyfin database (SQLite3)
SQLITE_FILE = '/nwithan8-cogs/jellyfin_manager/JellyfinDiscord.db' # File path + name + extension (i.e. "/root/nwithan8-cogs/jellyfin_manager/JellyfinDiscord.db"

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
subRoles = ["Monthly Subscriber","Yearly Subscriber", "Winner", "Bot"] # Exempt from removal
exemptsubs = [ADMIN_ID] # Discord IDs for users exempt from subscriber checks/deletion, separated by commas
SUB_CHECK_TIME = 7 # days

# Trial settings
TRIAL_ROLE_NAME = "Trial Member"
TRIAL_LENGTH = 24 # hours
TRIAL_CHECK_FREQUENCY = 15 # minutes
TRIAL_END_NOTIFICATION = "Hello, your " + str(TRIAL_LENGTH) + "-hour trial of " + str(SERVER_NICKNAME) + " has ended."

# Winner settings
WINNER_ROLE_NAME = "Winner"
WINNER_THRESHOLD = 7200 # 2 hours in seconds
AUTO_WINNERS = False
# True:
# Messages from the indicated GIVEAWAY_BOT_ID user will be scanned for mentioned Discord users (winners).
# The winners will be auto-assigned the TEMP_WINNER_ROLE_NAME. That role gives them access to a specificed WINNER_CHANNEL channel
# Users then post their Plex username (ONLY their Plex username) in the channel, which is processed by the bot.
# The bot invites the Plex username, and associates the Discord user author of the message with the Plex username in the database.
# The user is then have the TEMP_WINNER_ROLE_NAME role removed (which removes them from the WINNER_CHANNEL channel), and assigned the final WINNER_ROLE_NAME role.
TEMP_WINNER_ROLE_NAME = "Uninvited Winner"
WINNER_CHANNEL = 0 # Channel ID
GIVEAWAY_BOT_ID = 0


# Credentials settings
CREATE_PASSWORD = False
NO_PASSWORD_MESSAGE = "Leave password blank on first login, but please secure your account by setting a password."
USE_HASTEBIN = False
HASTEBIN_URL = 'https://hastebin.com'


# Migrate/mass import users
MIGRATION_FILE = "/" # file path + name (leave off ".csv" extension)

def j_get(cmd, params):
    """
    Returns JSON
    """
    return json.loads(requests.get(JELLYFIN_URL + "/jellyfin/" + cmd + "?api_key=" + JELLYFIN_KEY + ("&" + params if params != None else "")).text)

def j_post(cmd, params, payload):
    """
    Returns the request response. Must parse for JSON or status code in body code
    """
    return requests.post(JELLYFIN_URL + "/jellyfin/" + cmd + "?api_key=" + JELLYFIN_KEY + ("&" + params if params != None else ""), json=payload)

def j_delete(cmd, params):
    """
    Returns the request response. Must parse for JSON or status code in body code
    """
    return requests.delete(JELLYFIN_URL + "/jellyfin/" + cmd + "?api_key=" + JELLYFIN_KEY + ("&" + params if params != None else ""))

def password(length):
    """
    Generate a random string of letters and digits
    """
    lettersAndDigits = string.ascii_letters + string.digits
    return ''.join(random.choice(lettersAndDigits) for i in range(length))

def hastebin(content, url=HASTEBIN_URL):
    post = requests.post(f'{url}/documents', data=content.encode('utf-8'))
    return url + '/' + post.json()['key']

class Jellyfin(commands.Cog):
    
    def get_jellyfin_users(self):
        """
        Return dictionary {'user_name': 'user_id'}
        """
        users = {}
        for u in j_get("user_usage_stats/user_list", None):
            users[u['name']] = u['id']
        return users
    
    def add_to_jellyfin(self, username, discordId, note):
        """
        Add a Discord user to Jellyfin
        """
        try:
            p = None
            payload = {
                "Name": username
            }
            r = j_post("Users/New", None, payload)
            if r.status_code != 200:
                return r.reason, p
            else:
                r = json.loads(r.text)
                Id = r['Id']
                #p = password(length=10)
                #payload = {
                #    "Id": Id,
                #    "CurrentPw": 'raspberry',
                #    "NewPw": p,
                #    "ResetPassword": 'true'
                #}
                #r = requests.post(JELLYFIN_URL + "/Users/" + str(Id) + "/Password?api_key=" + JELLYFIN_KEY, json=payload)
                self.add_user_to_db(discordId, username, Id, note)
                payload = {
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
                    "EnableSubtitleManagement": "false",
                    "EnableAllDevices": "true",
                    "EnableAllChannels": "false",
                    "EnablePublicSharing": "false",
                    "BlockedChannels": [
                        "IPTV",
                        "TVHeadEnd Recordings"
                    ]
                }
                return j_post("Users/" + str(Id) + "/Policy", None, payload).status_code, p
        except Exception as e:
            print(e)
    
    def remove_from_jellyfin(self, id):
        """
        Remove a Discord user from Jellyfin
        Returns:
        200 - user found and removed successfully
        600 - user found, but not removed
        700 - user not found in database
        500 - unknown error
        """
        try:
            jellyfinId = self.find_user_in_db("Jellyfin", id)
            s = 200
            if not jellyfinId:
                s = 700
            else:
                payload = {
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
                #s = requests.post(JELLYFIN_URL + "/Users/" + str(jellyfinId) + "/Policy?api_key=" + JELLYFIN_KEY, json=payload).status_code
                # Doesn't delete user, instead makes deactive.
                # Delete function not documented in Jellyfin API, but exists in old Jellyfin API and still works
                r = j_delete("Users/" + str(jellyfinId), None)
                if not str(r.status_code).startswtth("2"):
                    s = 600
            if s == 200:
                self.remove_user_from_db(id)
            return str(s)
        except Exception as e:
            print(e)
            return "500"
    
    def describe_table(self, table):
        conn = sqlite3.connect(SQLITE_FILE)
        result = ""
        cur = conn.cursor()
        cur.execute("PRAGMA  table_info([" + str(table) + "])")
        result = cur.fetchall()
        cur.close()
        conn.close()
        if result:
            return result
        else:
            return None
            
    def add_user_to_db(self, DiscordId, JellyfinName, JellyfinId, note):
        conn = sqlite3.connect(SQLITE_FILE)
        cur = conn.cursor()
        query = ""
        if note == 't':
            query = "INSERT INTO users (DiscordID, JellyfinUsername, JellyfinID, ExpirationStamp, Note) VALUES ('{did}', '{ju}', '{jid}', '{time}', '{note}')".format(did=str(DiscordId), ju=str(JellyfinName), jid=str(JellyfinId), time=str(int(time.time()) + (3600 * TRIAL_LENGTH)), note=str(note))
        else:
            query = "INSERT INTO users (DiscordID, JellyfinUsername, JellyfinID, Note) VALUES ('{did}', '{ju}', '{jid}', '{note}')".format(did=str(DiscordId), ju=str(JellyfinName), jid=str(JellyfinId), note=str(note))
        cur.execute(str(query))
        conn.commit()
        cur.close()
        conn.close()
        
    def remove_user_from_db(self, id):
        conn = sqlite3.connect(SQLITE_FILE)
        cur = conn.cursor()
        cur.execute(str("DELETE FROM users WHERE DiscordID = " + str(id)))
        conn.commit()
        cur.close()
        conn.close()
            
    def find_user_in_db(self, JellyfinOrDiscord, data):
        """
        Returns JellyfinID/DiscordID
        """
        conn = sqlite3.connect(SQLITE_FILE)
        cur = conn.cursor()
        query = "SELECT " + ("JellyfinID" if JellyfinOrDiscord == "Jellyfin" else "DiscordID") + " FROM users WHERE " + ("DiscordID" if JellyfinOrDiscord == "Jellyfin" else "JellyfinID") + " = '" + str(data) + "'"
        cur.execute(str(query))
        result = cur.fetchone()
        cur.close()
        conn.close()
        if result:
            return result
        else:
            return None
        
    def find_username_in_db(self, JellyfinOrDiscord, data):
        """
        Returns JellyfinUsername/DiscordID, Note
        """
        conn = sqlite3.connect(SQLITE_FILE)
        cur = conn.cursor()
        query = "SELECT " + ("JellyfinUsername" if JellyfinOrDiscord == "Jellyfin" else "DiscordID") + ", Note FROM users WHERE " + ("DiscordID" if JellyfinOrDiscord == "Jellyfin" else "JellyfinUsername") + " = '" + str(data) + "'"
        cur.execute(str(query))
        result = cur.fetchone()
        cur.close()
        conn.close()
        if result:
            return result[0], result[1]
        else:
            return None, None
        
    def find_entry_in_db(self, type, data):
        """
        Returns whole entry
        """
        conn = sqlite3.connect(SQLITE_FILE)
        response = ""
        cur = conn.cursor()
        query = "SELECT * FROM users WHERE " + type + " = '" + str(data) + "'"
        cur.execute(query)
        result = cur.fetchone()
        cur.close()
        conn.close()
        if result:
            return result
        else:
            return None
        
    async def purge_winners(self, ctx):
        try:
            conn = sqlite3.connect(SQLITE_FILE)
            monitorlist = []
            cur = conn.cursor()
            cur.execute("SELECT JellyfinID FROM users WHERE Note = 'w'")
            for u in cur.fetchall():
                monitorlist.append(u[0])
            cur.close()
            conn.close()
            print("Winners: ")
            print(monitorlist)
            removed_list = ""
            error_message = ""
            for u in monitorlist:
                try:
                    payload = {"CustomQueryString": "SELECT SUM(PlayDuration) FROM PlaybackActivity WHERE UserId = '" + u + "' AND DateCreated >= date(julianday(date('now'))-14)", "ReplaceUserId": "false"}
                    # returns time watched in last 14 days, in seconds
                    time = j_post("user_usage_stats/submit_custom_query", None, payload)['results'][0][0]
                    if time == None:
                        time = 0
                    time = int(time)
                    if time < WINNER_THRESHOLD:
                        print(u + " has NOT met the duration requirements. Purging...")
                        mention_id = await self.remove_winner(str(u))
                        removed_list = removed_list + (mention_id if mention_id != None else "")
                except Exception as e:
                    print(e)
                    error_message = error_message + "Error checking " + str(u) + ". "
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
            
    async def remove_winner(self, jellyfinId):
        try:
            id = self.find_user_in_db("Discord", jellyfinId)
            if id != None:
                code = self.remove_from_jellyfin(jellyfinId)
                if code.startswith('2'):
                    user = self.bot.get_user(int(id))
                    await user.create_dm()
                    await user.dm_channel.send("You have been removed from " + str(SERVER_NICKNAME) + " due to inactivity.")
                    await user.remove_roles(discord.utils.get(self.bot.get_guild(int(SERVER_ID)).roles, name="Winner"), reason="Inactive winner")
                    return "<@" + id + ">, "
        except Exception as e:
            pass
        return None
        
    def remove_nonsub(self, memberID):
        if memberID not in exemptsubs:
            self.remove_from_jellyfin(memberID)
        
    @tasks.loop(seconds=SUB_CHECK_TIME*(3600*24))
    async def check_subs(self):
        print("Checking Jellyfin subs...")
        exemptRoles = []
        allRoles = self.bot.get_guild(int(SERVER_ID)).roles
        for r in allRoles:
            if r.name in subRoles:
                exemptRoles.append(r)
        for member in self.bot.get_guild(int(SERVER_ID)).members:
            if not any(x in member.roles for x in exemptRoles):
                self.remove_nonsub(member.id)
        print("Jellyfin Subs check completed.")
        
    @tasks.loop(seconds=TRIAL_CHECK_FREQUENCY*60)
    async def check_trials(self):
        print("Checking Jellyfin trials...")
        conn = sqlite3.connect(SQLITE_FILE)
        cur = conn.cursor()
        query = "SELECT DiscordID FROM users WHERE ExpirationStamp<=" + str(int(time.time())) + " AND Note = 't'";
        cur.execute(str(query))
        trial_role = discord.utils.get(self.bot.get_guild(int(SERVER_ID)).roles, name=TRIAL_ROLE_NAME)
        for u in cur:
            print("Ending trial for " + str(u[0]))
            self.remove_from_jellyfin(int(u[0]))
            try:
                user = self.bot.get_guild(int(SERVER_ID)).get_member(int(u[0]))
                await user.create_dm()
                await user.dm_channel.send(TRIAL_END_NOTIFICATION)
                await user.remove_roles(trial_role, reason="Trial has ended.")
            except Exception as e:
                print(e)
                print("Discord user " + str(u[0]) + " not found.")
        cur.close()
        conn.close()
        print("Jellyfin Trials check completed.")
        
    
    @commands.group(aliases=["Jellyfin", "jf", "JF"], pass_context=True)
    async def jellyfin(self, ctx: commands.Context):
        """
        Jellyfin Media Server commands
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")
            
    @jellyfin.command(name="access", pass_context=True)
    ### Anyone can use this command
    async def jellyfin_access(self, ctx: commands.Context, JellyfinUsername: str = None):
        """
        Check if you or another user has access to the Jellyfin server
        """
        hasAccess = False
        name = ""
        if JellyfinUsername is None:
            name, note = self.find_username_in_db("Jellyfin", ctx.message.author.id)
        else:
            name = JellyfinUsername
        if name in self.get_jellyfin_users().keys():
            await ctx.send(("You have" if JellyfinUsername is None else name + " has") + " access to " + SERVER_NICKNAME)
        else:
            await ctx.send(("You do" if JellyfinUsername is None else name + " does") + " not have access to " + SERVER_NICKNAME)
            
    @jellyfin_access.error
    async def jellyfin_access_error(self, ctx, error):
        await ctx.send("Sorry, something went wrong.")
            
    @jellyfin.command(name="status", aliases=['ping', 'up', 'online'], pass_context=True)
    ### Anyone can use this command
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
        await self.purge_winners(ctx)
        
    @jellyfin.command(name="count", aliases=["subs","number"], pass_context=True)
    @commands.has_role(ADMIN_ROLE_NAME)
    async def jellyfin_count(self, ctx: commands.Context):
        """
        Get the number of enabled Jellyfin users
        """
        count = len(self.get_jellyfin_users())
        if count > 0:
            await ctx.send(str(SERVER_NICKNAME) + " has " + str(count) + " users.")
        else:
            await ctx.send("An error occurred.")
            
    @jellyfin_count.error
    async def jellyfin_count_error(self, ctx, error):
        await ctx.send("Something went wrong. Please try again later.")
    
    @jellyfin.command(name="add", aliases=["new","join"], pass_context=True)
    @commands.has_role(ADMIN_ROLE_NAME)
    async def jellyfin_add(self, ctx: commands.Context, user: discord.Member, username: str):
        """
        Add a Discord user to Jellyfin
        """
        s, p = self.add_to_jellyfin(username, user.id, 's')
        if str(s).startswith("2"):
            await user.create_dm()
            creds = ""
            if USE_HASTEBIN:
                creds = hastebin("Hostname: " + str(JELLYFIN_URL) + "\nUsername: " + str(username) + "\n" + ("Password: " + p if CREATE_PASSWORD else NO_PASSWORD_MESSAGE) + "\n")
            else:
                creds = "Hostname: " + str(JELLYFIN_URL) + "\nUsername: " + str(username) + "\n" + ("Password: " + p if CREATE_PASSWORD else NO_PASSWORD_MESSAGE) + "\n"
            await user.dm_channel.send("You have been added to " + str(SERVER_NICKNAME) + "!\n" + creds)
            await ctx.send("You've been added, " + user.mention + "! Please check your direct messages for login information.")
        else:
            await ctx.send("An error occurred while adding " + user.mention)
            
    @jellyfin_add.error
    async def jellyfin_add_error(self, ctx, error):
        await ctx.send("Please mention the Discord user to add to Jellyfin, as well as their Jellyfin username.")
            
    @jellyfin.command(name="remove", aliases=["delete","rem"], pass_context=True)
    @commands.has_role(ADMIN_ROLE_NAME)
    async def jellyfin_remove(self, ctx: commands.Context, user: discord.Member):
        """
        Delete a Discord user from Jellyfin
        """
        s = self.remove_from_jellyfin(user.id)
        if str(s).startswith("2"):
            await ctx.send("You've been removed from " + str(SERVER_NICKNAME) + ", " + user.mention + ".")
        elif str(s).startswith("6"):
            await ctx.send(user.mention + " could not be removed.")
        elif str(s).startswith("7"):
            await ctx.send("There are no accounts for " + user.mention)
        else:
            await ctx.send("An error occurred while removing " + user.mention)
            
    @jellyfin_remove.error
    async def jellyfin_remove_error(self, ctx, error):
        await ctx.send("Please mention the Discord user to remove from Jellyfin.")
        
    @jellyfin.command(name="trial", pass_context=True)
    @commands.has_role(ADMIN_ROLE_NAME)
    async def jellyfin_trial(self, ctx: commands.Context, user: discord.Member, JellyfinUsername: str):
        """
        Start a trial of Jellyfin
        """
        s, p  = self.add_to_jellyfin(JellyfinUsername, user.id, 't')
        if str(s).startswith("2"):
            await user.create_dm()
            creds = ""
            if USE_HASTEBIN:
                creds = hastebin("Hostname: " + str(JELLYFIN_URL) + "\nUsername: " + str(username) + "\n" + ("Password: " + p if CREATE_PASSWORD else NO_PASSWORD_MESSAGE) + "\n")
            else:
                creds = "Hostname: " + str(JELLYFIN_URL) + "\nUsername: " + str(username) + "\n" + ("Password: " + p if CREATE_PASSWORD else NO_PASSWORD_MESSAGE) + "\n"
            await user.dm_channel.send("You have been added to " + str(SERVER_NICKNAME) + "!\n" + creds)
            await ctx.send("You've been added, " + user.mention + "! Please check your direct messages for login information.")
        else:
            await ctx.send("An error occurred while starting a trial for " + user.mention)
            
    @jellyfin_trial.error
    async def jellyfin_trial_error(self, ctx, error):
        await ctx.send("Please mention the Discord user to add to Jellyfin, as well as their Jellyfin username.")
        
    @jellyfin.command(name="import", pass_context=True)
    @commands.has_role(ADMIN_ROLE_NAME)
    async def jellyfin_import(self, ctx: commands.Context, user: discord.Member, JellyfinUsername: str, subType: str, serverNumber: int = None):
        """
        Add existing Jellyfin users to the database.
        user - tag a Discord user
        JellyfinUsername - Jellyfin username of the Discord user
        subType - custom note for tracking subscriber type; MUST be less than 5 letters.
        Default in database: 's' for Subscriber, 'w' for Winner, 't' for Trial.
        NOTE: subType 't' will make a new 24-hour timestamp for the user.
        """
        users = self.get_jellyfin_users()
        if JellyfinUsername not in users.keys():
            await ctx.send("Not an existing Jellyfin user.")
        else:
            jellyfinId = users[JellyfinUsername]
            if len(subType) > 4:
                await ctx.send("subType must be less than 5 characters long.")
            else:
                new_entry = self.add_user_to_db(user.id, JellyfinUsername, JellyfinId, subType)
                if new_entry:
                    if subType == 't':
                        await ctx.send("Trial user was added/new timestamp issued.")
                    else:
                        await ctx.send("User added to the database.")
                else:
                    await ctx.send("User already exists in the database.")
                    
    @jellyfin_import.error
    async def jellyfin_import_error(self, ctx, error):
        await ctx.send("Please mention the Discord user to add to the database, including their Plex username and sub type.")
        
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
        name, note = self.find_username_in_db("Jellyfin", user.id)
        if name:
            await ctx.send(user.mention + " is Jellyfin user: " + name + (" [Trial]" if note == 't' else " [Subscriber]"))
        else:
            await ctx.send("User not found.")
        
    @jellyfin_find.command(name="discord", aliases=["d"])
    async def jellyfin_find_discord(self, ctx: commands.Context, JellyfinUsername: str):
        """
        Find Jellyfin user's Discord name
        """
        id, note = self.find_username_in_db("Discord", JellyfinUsername)
        if id:
            await ctx.send(JellyfinUsername + " is Discord user: " + self.bot.get_user(int(id)).mention)
        else:
            await ctx.send("User not found.")
            
    @jellyfin_find.error
    async def jellyfin_find_error(self, ctx, error):
        await ctx.send("An error occurred while looking for that user.")
            
    @jellyfin.group(name="info")
    @commands.has_role(ADMIN_ROLE_NAME)
    async def jellyfin_info(self, ctx: commands.Context):
        """
        Get database entry for a user
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")
            
    @jellyfin_info.command(name="jellyfin", aliases=["e"])
    async def jellyfin_info_jellyfin(self, ctx, JellyfinUsername: str):
        """
        Get database entry for Jellyfin username
        """
        embed = discord.Embed(title=("Info for " + str(JellyfinUsername)))
        n = self.describe_table("users")
        d = self.find_entry_in_db("JellyfinUsername", JellyfinUsername)
        if d:
            for i in range(0,len(n)):
                val=str(d[i])
                if str(n[i][1]) == "DiscordID":
                    val=val+" ("+self.bot.get_user(int(d[i])).mention+")"
                if str(n[i][1]) == "Note":
                    val=("Trial" if d[i] == 't' else "Subscriber")
                if d[i] != None:
                    embed.add_field(name=str(n[i][1]),value=val,inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send("That user is not in the database.")
        
    @jellyfin_info.command(name="discord", aliases=["d"])
    async def jellyfin_info_discord(self, ctx, user: discord.Member):
        """
        Get database entry for Discord user
        """
        embed = discord.Embed(title=("Info for " + user.name))
        n = self.describe_table("users")
        d = self.find_entry_in_db("DiscordID", user.id)
        if d:
            for i in range(0,len(n)):
                name=str(n[i][1])
                val=str(d[i])
                if str(n[i][1]) == "DiscordID":
                    val=val+" ("+self.bot.get_user(int(d[i])).mention+")"
                if str(n[i][1]) == "Note":
                    val=("Trial" if d[i] == 't' else "Subscriber")
                if d[i] != None:
                    embed.add_field(name=str(n[i][1]),value=val,inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send("That user is not in the database.")
        
    @jellyfin_info.error
    async def jellyfin_info_error(self, ctx, error):
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
                jellyfin_username = row['Discord_Tag'].split("#")[0] # Jellyfin username will be Discord username
                user = discord.utils.get(ctx.message.guild.members, name=jellyfin_username)
                s, p = self.add_to_jellyfin(jellyfin_username, user.id, 's') # Users added as 'Subscribers'
                if str(s).startswith("2"):
                    await user.create_dm()
                    creds = ""
                    if USE_HASTEBIN:
                        creds = hastebin("Hostname: " + str(JELLYFIN_URL) + "\nUsername: " + str(username) + "\n" + ("Password: " + p if CREATE_PASSWORD else NO_PASSWORD_MESSAGE) + "\n")
                    else:
                        creds = "Hostname: " + str(JELLYFIN_URL) + "\nUsername: " + str(username) + "\n" +("Password: " + p if CREATE_PASSWORD else NO_PASSWORD_MESSAGE) + "\n"
                    await user.dm_channel.send("You have been added to " + str(SERVER_NICKNAME) + "!\n" + creds)
                    #await ctx.send("You've been added, " + user.mention + "! Please check your direct messages for login information.")
                    data = [str(row['Discord_Tag']), str(row['Plex_Username']), str(jellyfin_username)]
                    writer.writerow(data)
                    count += 1
                else:
                    failed.append(jellyfin_username)
            f.close()
        await ctx.send(str(count) + " users added to Jellyfin." + ("" if len(failed) == 0 else "The following users were not added successfully: " + "\n".join(failed)))
        
        
    @commands.Cog.listener()
    async def on_message(self, message):
        if AUTO_WINNERS:
            if message.author.id == GIVEAWAY_BOT_ID and "congratulations" in message.content.lower() and message.mentions:
                tempWinner = discord.utils.get(message.guild.roles, name=TEMP_WINNER_ROLE_NAME)
                for u in message.mentions:
                    await u.add_roles(tempWinner, reason="Winner - access winner invite channel")
            if message.channel.id == WINNER_CHANNEL and discord.utils.get(message.guild.roles, name=TEMP_WINNER_ROLE_NAME) in message.author.roles:
                username = message.content.strip() #Only include username, nothing else
                s, p = self.add_to_jellyfin(username, message.author.id, 'w')
                if str(s).startswith("2"):
                    await user.create_dm()
                    creds = ""
                    if USE_HASTEBIN:
                        creds = hastebin("Hostname: " + str(JELLYFIN_URL) + "\nUsername: " + str(username) + "\n" + ("Password: " + p if CREATE_PASSWORD else NO_PASSWORD_MESSAGE) + "\n")
                    else:
                        creds = "Hostname: " + str(JELLYFIN_URL) + "\nUsername: " + str(username) + "\n" +("Password: " + p if CREATE_PASSWORD else NO_PASSWORD_MESSAGE) + "\n"
                    await user.dm_channel.send("You have been added to " + str(SERVER_NICKNAME) + "!\n" + creds)
                    await ctx.send("You've been added, " + user.mention + "! Please check your direct messages for login information.")
                    await message.author.remove_roles(discord.utils.get(message.guild.roles, name=TEMP_WINNER_ROLE_NAME), reason="Winner was processed successfully.")
                else:
                    if "exist" in s:
                        await ctx.send(s)
                    else:
                        await ctx.send("An error occurred while adding " + message.author.mention)
        
    @commands.Cog.listener()
    async def on_ready(self):
        self.check_trials.start()
        self.check_subs.start()
            
    def __init__(self, bot):
        self.bot = bot
        print("Jellyfin Manager ready to go.")
