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
import mysql.connector
import os
import datetime
from decimal import *
import math
import asyncio
import random
import string


#Discord-to-Emby database credentials
hostname = os.environ.get('DATABASE_HOST')
port = os.environ.get('DATABASE_PORT')
username = os.environ.get('DATABASE_USER')
password = os.environ.get('DATABASE_PASS')
database = 'EmbyDiscord'

'''
Database schema:

EmbyDiscord.users
(DiscordID BIGINT, EmbyUsername 'VARCHAR(100)', EmbyID 'VARCHAR(100)')
'''

EMBY_URL = os.environ.get('EMBY_URL')
EMBY_KEY = os.environ.get('EMBY_KEY')
SERVER_NICKNAME = os.environ.get('EMBY_SERVER_NAME')

# Discord (Admin) settings
SERVER_ID = os.environ.get('DISCORD_SERVER_ID')
ADMIN_ID = os.environ.get('ADMIN_ID')
ADMIN_ROLE_NAME = "Admin"
afterApprovedRoleName = "Invited"
subRoles = ["Monthly Subscriber","Yearly Subscriber", "Winner", "Bot"] # Exempt from removal
exemptsubs = [ADMIN_ID] # Discord IDs for users exempt from subscriber checks/deletion, separated by commas
SUB_CHECK_TIME = 7 # days

REACT_TO_ADD = False
# False:
# The Discord administrator types "pm add <@DiscordUser> <EmbyUsername>".
# The mentioned Discord user will be associated with the corresponding Emby username.
# "pm remove <@DiscordUser>" will remove the mentioned Discord user's Emby access.
#
# True:
# A user posts their Emby username in a Discord channel.
# The "ADMIN_ID" Discord administrator reacts to the message with the "approvedEmojiName" emoji. (Must be that emoji, must be that one Discord administrator)
# The bot then automatically adds the user to Emby and other services.
# This works for regular users, as well as those with the WINNER_ROLE_NAME role. This DOES NOT WORK for those with the TRIAL_ROLE_NAME role
# Users must be the one to post their username, since the bot links the posting user with the corresponding Emby username.
# Removing the emoji will trigger an uninvite.
#
# React-to-add is faster (one-click add, rather than typing), but requires users to post their own username.
# Also, if the bot reboots, it will not see reactions added to messages prior to it coming online (adding/removing reactions to older messages will not trigger the add/remove functions)

approvedEmojiName = "approved"

# Trial settings
TRIAL_ROLE_NAME = "Trial Member"
TRIAL_LENGTH = 24 # hours
TRIAL_CHECK_FREQUENCY = 15 # minutes
TRIAL_END_NOTIFICATION = "Hello, your " + str(TRIAL_LENGTH) + "-hour trial of " + SERVER_NICKNAME + " has ended."

# Winner settings
WINNER_ROLE_NAME = "Winner"
WINNER_THRESHOLD = 2 # hours

# Logging settings
FRIENDLY_LOGGING = False
#FRIENDLY_LOG_CHANNEL_ID = ###########
VERBOSE_LOGGING = False
#VERBOSE_LOG_CHANNEL_ID = ###############

class Emby(commands.Cog):
    def add_to_emby(self, username, discordId, note):
        payload = {
            "Name": username
        }
        r = json.loads(requests.post(EMBY_URL + "/Users/New?api_key=" + EMBY_KEY, json=payload).text)
        #p = self.password(length=10)
        #print(p)
        Id = r['Id']
        #r = requests.post(EMBY_URL + "/Users/" + str(Id) + "/Password?api_key=" + EMBY_KEY, json=payload) # CANNOT CURRENTLY SET PASSWORD FOR NEW USER
        #print(r.status_code)
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
        return requests.post(EMBY_URL + "/Users/" + str(Id) + "/Policy?api_key=" + EMBY_KEY, json=payload).status_code
    
    def remove_from_emby(self, id):
        """
        Delete a Discord user from Emby
        """
        embyId = self.find_user_in_db("Emby", id)
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
        #s = requests.post(EMBY_URL + "/Users/" + str(embyId) + "/Policy?api_key=" + EMBY_KEY, json=payload).status_code
        # Doesn't delete user, instead makes deactive.
        # Delete function not documented in Emby API, but exists in old Emby API and still works
        s = requests.delete(EMBY_URL + "/Users/" + str(embyId) + "?api_key=" + EMBY_KEY).status_code
        self.remove_user_from_db(id)
        return s
    
    def check_db(self, data, type):
        conn = mysql.connector.connect(host=hostname,port=port,user=username,passwd=password,db=database)
        response = ""
        if conn.is_connected():
            cur = conn.cursor(buffered=True)
            query = "SELECT * FROM regular_users WHERE " + ("DiscordID" if type == "Discord" else "EmbyUsername") + " = " + str(data)
            cur.execute(query)
            for el in cur.fetchone:
                for i in range(0, len(cur.description)):
                    response = response + cur.description[i][0] + " " + el[i] + "\n"
            cur.close()
            conn.close()
            return response
            
    def add_user_to_db(self, discordId, embyUsername, EmbyID, note):
        myConnection = mysql.connector.connect(host=hostname,port=port,user=username,passwd=password,db=database)
        if myConnection.is_connected():
            cursor = myConnection.cursor(buffered=True)
            query = ""
            if note == 't':
                query = "INSERT INTO users (DiscordID, EmbyUsername, EmbyID, ExpirationStamp, Note) VALUES ('" + str(discordId) + "','" + str(embyUsername) + "','" + str(embyId) + "','" + str(int(time.time()) + (3600 * TRIAL_LENGTH)) + "','" + str(note) + "')"
            else:
                query = "INSERT INTO users (DiscordID, EmbyUsername, EmbyID, Note) VALUES ('" + str(discordId) + "','" + str(embyUsername) + "','" + str(embyId) + "','" + str(note) + "')"
            cursor.execute(str(query))
            myConnection.commit()
            cursor.close()
            myConnection.close()
        
    def remove_user_from_db(self, id):
        myConnection = mysql.connector.connect(host=hostname,port=port,user=username,passwd=password,db=database)
        if myConnection.is_connected():
            cursor = myConnection.cursor(buffered=True)
            cursor.execute(str("DELETE FROM users WHERE DiscordID = " + str(id)))
            myConnection.commit()
            cursor.close()
            myConnection.close()
            
    def find_user_in_db(self, EmbyOrDiscord, data):
        myConnection = mysql.connector.connect(host=hostname,port=port,user=username,passwd=password,db=database)
        if myConnection.is_connected():
            cursor = myConnection.cursor()
            query = "SELECT " + ("EmbyID" if EmbyOrDiscord == "Emby" else "DiscordID") + " FROM users WHERE " + ("DiscordID" if EmbyOrDiscord == "Emby" else "EmbyID") + " = '" + str(data) + "'"
            cursor.execute(str(query))
            result = cursor.fetchone()[0]
            cursor.close()
            myConnection.close()
            return result
        
    def remove_nonsub(self, memberID):
        if memberID not in exemptsubs:
            self.remove_from_emby(memberID)
        
    @tasks.loop(seconds=SUB_CHECK_TIME*(3600*24))
    async def check_subs(self):
        myConnection = mysql.connector.connect(host=hostname,port=port,user=username,passwd=password,db=database)
        #await self.log("Checking non-subscribers.", "v")
        cur = myConnection.cursor(buffered=True)
        query = "SELECT * FROM users"
        cur.execute(str(query))
        ##await self.log("Database preview:\n" + str(cur.fetchall()))
        exemptRoles = []
        allRoles = self.bot.get_guild(SERVER_ID).roles
        for r in allRoles:
            if r.name in subRoles:
                exemptRoles.append(r)
        for member in self.bot.get_guild(SERVER_ID).members:
            if not any(x in member.roles for x in exemptRoles):
                await self.remove_nonsub(member.id)
        myConnection.close()
        
    @tasks.loop(seconds=TRIAL_CHECK_FREQUENCY*60)
    async def check_trials(self):
        myConnection = mysql.connector.connect(host=hostname,port=port,user=username,passwd=password,db=database)
        if myConnection.is_connected():
            cur = myConnection.cursor(buffered=True)
            query = "SELECT DiscordID FROM users WHERE ExpirationStamp<=" + str(int(time.time())) + " AND Note = 't'";
            cur.execute(str(query))
            trial_role = discord.utils.get(self.bot.get_guild(SERVER_ID).roles, name=TRIAL_ROLE_NAME)
            for u in cur:
                await self.remove_from_emby(u[0])
                user = self.bot.get_guild(SERVER_ID).get_member(u[0])
                await user.create_dm()
                await user.dm_channel.send(TRIAL_END_NOTIFICATION)
                await user.remove_roles(trial_role, reason="Trial has ended.")
                await self.remove_user_from_db(u[0])
            cur.close()
            myConnection.close()
        
    def password(self, length):
        """Generate a random string of letters and digits """
        lettersAndDigits = string.ascii_letters + string.digits
        return ''.join(random.choice(lettersAndDigits) for i in range(length))
    
    def r_post(self, cmd, params):
        return json.loads(requests.post(EMBY_URL + "/" + cmd + "?api_key=" + EMBY_KEY).text)
    
    def r_get(self, cmd, params):
        return json.loads(requests.get(EMBY_URL + "/" + cmd + "?api_key=" + EMBY_KEY).text)
    
    def r_delete(self, cmd, params):
        return json.loads(requests.delete(EMBY_URL + "/" + cmd + "?api_key=" + EMBY_KEY).text)
        
    #def request(self, cmd, params):
    #    return json.loads(requests.get(EMBY_URL + "/" + cmd + "?apikey=" + TAUTULLI_API_KEY + "&" + str(params) + "&cmd=" + str(cmd)).text if params != None else requests.get(TAUTULLI_BASE_URL + "/api/v2?apikey=" + TAUTULLI_API_KEY + "&cmd=" + str(cmd)).text)
    
    @commands.group(aliases=["Emby", "em"], pass_context=True)
    @commands.has_role(ADMIN_ROLE_NAME)
    async def emby(self, ctx: commands.Context):
        """
        Emby Media Server commands
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")
    
    @emby.command(name="add", aliases=["new","join"], pass_context=True)
    async def emby_add(self, ctx: commands.Context, user: discord.Member, username: str):
        """
        Add a Discord user to Emby
        """
        s = self.add_to_emby(username, user.id, 's')
        if str(s).startswith("2"):
            await user.create_dm()
            await user.dm_channel.send("You have been added to " + SERVER_NICKNAME + "!\n" +
                                       "Hostname: " + EMBY_URL + "\n" +
                                       "Username: " + username + "\n" +
                                       "Leave password blank on first login, but please secure your account by setting a password.\n" + 
                                       "Have fun!")
            await ctx.send("You've been added, " + user.mention + "! Please check your direct messages for login information.")
        else:
            await ctx.send("An error occurred while adding " + user.mention)
            
    @emby_add.error
    async def emby_add_error(self, ctx, error):
        await ctx.send("Please mention the Discord user to add to Emby, as well as their Emby username.")
            
    @emby.command(name="remove", aliases=["delete","rem"], pass_context=True)
    async def emby_remove(self, ctx: commands.Context, user: discord.Member):
        """
        Delete a Discord user from Emby
        """
        s = await self.remove_from_emby(user.id)
        if str(s).startswith("2"):
            await ctx.send("You've been removed from " + SERVER_NICKNAME + ", " + user.mention + ".")
        else:
            await ctx.send("An error occurred while removing " + user.mention)
            
    @emby_remove.error
    async def emby_remove_error(self, ctx, error):
        await ctx.send("Please mention the Discord user to remove from Emby.")
        
    @emby.command(name="trial")
    @commands.has_role(ADMIN_ROLE_NAME)
    async def emby_trial(self, ctx: commands.Context, user: discord.Member, EmbyUsername: str):
        s = await self.add_to_emby(EmbyUsername, user.id, 't')
        if str(s).startswith("2"):
            await user.create_dm()
            await user.dm_channel.send("You have been granted a " + str(TRIAL_LENGTH) + "-hour trial to " + SERVER_NICKNAME + "!\n" +
                                       "Hostname: " + EMBY_URL + "\n" +
                                       "Username: " + username + "\n" +
                                       "Leave password blank on first login, but please secure your account by setting a password.\n" + 
                                       "Have fun!")
            await ctx.send("Your trial of " + SERVER_NICKNAME + " has begun, " + user.mention + "! Please check your direct messages for login information.")
        else:
            await ctx.send("An error occurred while starting a trial for " + user.mention)
            
    @emby_trial.error
    async def pm_trial_error(self, ctx, error):
        await ctx.send("Please mention the Discord user to add to Emby, as well as their Emby username.")
            
    @emby.command(name="count", aliases=["subs","number"], pass_context=True)
    async def emby_count(self, ctx: commands.Context):
        """
        Get the number of enabled Emby users
        """
        count = len(json.loads(requests.get(EMBY_URL + "/Users?api_key=" + EMBY_KEY).text))
        if count > 0:
            await ctx.send(SERVER_NICKNAME + " has " + str(count) + " users.")
        else:
            await ctx.send("An error occurred.")
            
    @emby_count.error
    async def emby_count_error(self, ctx, error):
        await ctx.send("Something went wrong. Please try again later.")
            
    def __init__(self, bot):
        self.bot = bot
        print("Emby Manager ready to go.")
