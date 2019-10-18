import discord
from discord.ext import commands, tasks
from discord.utils import get
from collections import defaultdict
from plexapi.server import PlexServer
import plexapi
from plexapi.myplex import MyPlexAccount
import mysql.connector
import random
import re
import json
import requests
import os
import datetime
from decimal import *
import math
import asyncio
import random
import string
import time


# Database credentials
dbhostname = os.environ.get('DATABASE_HOST')
dbport = os.environ.get('DATABASE_PORT')
dbusername = os.environ.get('DATABASE_USER')
dbpassword = os.environ.get('DATABASE_PASS')
JellyfinDatabase = 'JellyfinDiscord'
EmbyDatabase = 'EmbyDiscord'
PlexDatabase = 'PlexDiscord'

'''
Database schema:

JellyfinDiscord.users
(DiscordID BIGINT, JellyfinUsername 'VARCHAR(100)', JellyfinID 'VARCHAR(100)')
'''

SERVER_NICKNAME = os.environ.get('EMBY_SERVER_NAME')

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
TRIAL_END_NOTIFICATION = "Hello, your " + str(TRIAL_LENGTH) + "-hour trial of " + str(SERVER_NICKNAME) + " has ended."

PAYMENT_MSG = "Payments can be made at https://shoppy.gg/@CrashpiG"
PRICES = {
    "CrashCourse Media Server Only":{
        "1 Month":"$8",
        "3 Months":"$21",
        "6 Months":"$40",
        "12 Months":"$75"
    },
    "IPTV":{
        "1 Month":"$10",
        "3 Months":"$28",
        "6 Months":"$54",
        "12 Months":"$100"
    },
    "CrashCourse Media Server + IPTV":{
        "1 Month":"$18",
        "3 Months":"$50",
        "6 Months":"$95",
        "12 Months":"$180"
    }
}


## DO NOT EDIT
JELLYFIN_URL = os.environ.get('JELLYFIN_URL')
JELLYFIN_KEY = os.environ.get('JELLYFIN_KEY')

EMBY_URL = os.environ.get('EMBY_URL')
EMBY_KEY = os.environ.get('EMBY_KEY')

# Ombi settings
USE_OMBI = True

# Tautulli settings
USE_TAUTULLI = True

plex = PlexServer(os.environ.get('PLEX_URL'), os.environ.get('PLEX_TOKEN'))
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
    approve_header = {'ApiKey': os.environ.get('OMBI_KEY'), 'accept': 'application/json', 'Content-Type': 'application/json-patch+json'}
    ombi_headers = {'ApiKey': os.environ.get('OMBI_KEY')}
if USE_TAUTULLI:
    TAUTULLI_URL = os.environ.get('TAUTULLI_URL') + "/api/v2?apikey=" + os.environ.get('TAUTULLI_KEY') + "&cmd="
    
## CODE BELOW

class Crashy(commands.Cog):
    def t_request(self, cmd, params):
        return json.loads(requests.get(os.environ.get('TAUTULLI_URL') + "/api/v2?apikey=" + os.environ.get('TAUTULLI_KEY') + "&cmd=" + str(cmd) + (("&" + str(params)) if params != None else "")).text)
    
    def add_to_tautulli(self, plexname):
        if USE_TAUTULLI == False:
            pass
        else:
            response = self.t_request("refresh_users_list",None)
        
    def delete_from_tautulli(self, plexname):
        if USE_TAUTULLI == False:
            pass
        else:
            response = self.t_request("delete_user","user_id=" + str(plexname))
        
    def add_to_ombi(self, plexname):
        if USE_OMBI == False:
            pass
        else:
            requests.post(ombi_import,headers=ombi_headers)

    def delete_from_ombi(self, plexname):
        if USE_OMBI == False:
            pass
        else:
            data = requests.get(ombi_users,headers=ombi_headers).json()
            id = ""
            for i in data:
                if i['userName'].lower() == plexname:
                    id = i['id']
            delete = str(ombi_delete) + str(id)
            requests.delete(delete, headers=ombi_headers)

    def add_to_plex(self, plexname, discordId, note):
        try:
            plex.myPlexAccount().inviteFriend(user=plexname,server=plex,sections=None, allowSync=False, allowCameraUpload=False, allowChannels=False, filterMovies=None, filterTelevision=None, filterMusic=None)
            self.add_plex_user_to_db(discordId, plexname, note)
            asyncio.sleep(60)
            self.add_to_tautulli(plexname)
            if note != 't': # Trial members do not have access to Ombi
                self.add_to_ombi(plexname)
            return True
        except Exception as e:
            return False
        
    def delete_from_plex(self, id):
        try:
            plexname = self.find_user_in_db("Plex","Plex",id)
            plex.myPlexAccount().removeFriend(user=plexname)
            self.delete_from_ombi(plexname) # Error if trying to remove trial user that doesn't exist in Ombi?
            self.delete_from_tautulli(plexname)
            self.remove_user_from_db(id, PlexDatabase)
            return True
        except plexapi.exceptions.NotFound:
            return False
    
    def add_to_jellyfin(self, username, discordId, note):
        try:
            payload = {
                "Name": username
            }
            r = json.loads(requests.post(JELLYFIN_URL + "/Users/New?api_key=" + JELLYFIN_KEY, json=payload).text)
            #p = self.password(length=10)
            #print(p)
            Id = r['Id']
            #r = requests.post(JELLYFIN_URL + "/Users/" + str(Id) + "/Password?api_key=" + JELLYFIN_KEY, json=payload) # CANNOT CURRENTLY SET PASSWORD FOR NEW USER
            #print(r.status_code)
            self.add_jellyfin_user_to_db(discordId, username, Id, note)
            #self.add_jellyfin_user_to_db(discordId, username, 'f36ddf47b06a460bb1045e6ad502d5fe', note)
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
            return requests.post(JELLYFIN_URL + "/Users/" + str(Id) + "/Policy?api_key=" + JELLYFIN_KEY, json=payload).status_code
        except Exception as e:
            print(e)
    
    def remove_from_jellyfin(self, id):
        """
        Delete a Discord user from Jellyfin
        """
        try:
            jellyfinIds = self.find_user_in_db("Jellyfin", "Jellyfin", id)
            s = 200
            if not jellyfinIds:
                s = 900
            else:
                status_codes = []
                for jellyfinId in jellyfinIds:
                    jellyfinId = jellyfinId[0]
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
                    status_codes.append(requests.delete(JELLYFIN_URL + "/Users/" + str(jellyfinId) + "?api_key=" + JELLYFIN_KEY).status_code)
                self.remove_user_from_db(id, JellyfinDatabase)
                for code in status_codes:
                    if not str(code).startswith("2"):
                        s = 700
                        break
            return s
        except Exception as e:
            print(e)
            
    def add_to_emby(self, username, discordId, note):
        try:
            payload = {
                "Name": username
            }
            r = json.loads(requests.post(EMBY_URL + "/Users/New?api_key=" + EMBY_KEY, json=payload).text)
            #p = self.password(length=10)
            #print(p)
            Id = r['Id']
            #r = requests.post(EMBY_URL + "/Users/" + str(Id) + "/Password?api_key=" + EMBY_KEY, json=payload) # CANNOT CURRENTLY SET PASSWORD FOR NEW USER
            #print(r.status_code)
            self.add_emby_user_to_db(discordId, username, Id, note)
            #self.add_emby_user_to_db(discordId, username, 'f36ddf47b06a460bb1045e6ad502d5fe', note)
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
        except Exception as e:
            print(e)
    
    def remove_from_emby(self, id):
        """
        Delete a Discord user from Emby
        """
        try:
            embyIds = self.find_user_in_db("Emby", "Emby", id)
            s = 200
            if not embyIds:
                s = 900
            else:
                status_codes = []
                for embyId in embyIds:
                    embyId = embyId[0]
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
                    status_codes.append(requests.delete(EMBY_URL + "/Users/" + str(embyId) + "?api_key=" + EMBY_KEY).status_code)
                self.remove_user_from_db(id, EmbyDatabase)
                for code in status_codes:
                    if not str(code).startswith("2"):
                        s = 700
                        break
            return s
        except Exception as e:
            print(e)
            
    def add_jellyfin_user_to_db(self, DiscordID, JellyfinUsername, JellyfinID, note):
        myConnection = mysql.connector.connect(host=dbhostname,port=dbport,user=dbusername,passwd=dbpassword,db=JellyfinDatabase)
        if myConnection.is_connected():
            cursor = myConnection.cursor(buffered=True)
            if note == 't':
                cursor.execute("INSERT INTO users (DiscordID, JellyfinUsername, JellyfinID, ExpirationStamp, Note) VALUES (%s, %s, %s, %s, %s)", (str(DiscordID), str(JellyfinUsername), str(JellyfinID), str(int(time.time()) + (3600 * TRIAL_LENGTH)), str(note)))
            else:
                cursor.execute("INSERT INTO users (DiscordID, JellyfinUsername, JellyfinID, Note) VALUES (%s, %s, %s, %s)", (DiscordID, JellyfinUsername, JellyfinID, note))
            myConnection.commit()
            cursor.close()
            myConnection.close()
            
    def add_emby_user_to_db(self, DiscordID, EmbyUsername, EmbyID, note):
        myConnection = mysql.connector.connect(host=dbhostname,port=dbport,user=dbusername,passwd=dbpassword,db=database)
        if myConnection.is_connected():
            cursor = myConnection.cursor(buffered=True)
            if note == 't':
                cursor.execute("INSERT INTO users (DiscordID, EmbyUsername, EmbyID, ExpirationStamp, Note) VALUES (%s, %s, %s, %s, %s)", (str(DiscordID), str(EmbyUsername), str(EmbyID), str(int(time.time()) + (3600 * TRIAL_LENGTH)), str(note)))
            else:
                cursor.execute("INSERT INTO users (DiscordID, EmbyUsername, EmbyID, Note) VALUES (%s, %s, %s, %s)", (DiscordID, EmbyUsername, EmbyID, note))
            myConnection.commit()
            cursor.close()
            myConnection.close()
            
    def add_plex_user_to_db(self, DiscordID, PlexUsername, note):
        myConnection = mysql.connector.connect(host=hostname,port=port,user=username,passwd=password,db=PlexDatabase)
        if myConnection.is_connected():
            cursor = myConnection.cursor(buffered=True)
            if note == 't':
                cursor.execute("INSERT INTO users (DiscordID, PlexUsername, ExpirationStamp, Note) VALUES (%s, %s, %s, %s)", (str(DiscordID), str(PlexUsername), str(int(time.time()) + (3600 * TRIAL_LENGTH)), str(note)))
                #query = "INSERT INTO users (DiscordID, PlexUsername, ExpirationStamp, Note) VALUES ('" + str(discordId) + "','" + str(plexUsername) + "','" + str(int(time.time()) + (3600 * TRIAL_LENGTH)) + "','" + str(note) + "')"
            else:
                cursor.execute("INSERT INTO users (DiscordID, PlexUsername, Note) VALUES (%s, %s, %s)", (str(DiscordID), str(PlexUsername), str(note)))
                #query = "INSERT INTO users (DiscordID, PlexUsername, Note) VALUES ('" + str(discordId) + "','" + str(plexUsername) + "','" + str(note) + "')"
            myConnection.commit()
            cursor.close()
            myConnection.close()
        
    def remove_user_from_db(self, id, whichdb):
        # Remove from Jellyfin
        myConnection = mysql.connector.connect(host=dbhostname,port=dbport,user=dbusername,passwd=dbpassword,db=whichdb)
        if myConnection.is_connected():
            cursor = myConnection.cursor(buffered=True)
            cursor.execute(str("DELETE FROM users WHERE DiscordID = " + str(id)))
            myConnection.commit()
            cursor.close()
            myConnection.close()
            
    def find_user_in_db(self, platformOrDiscord, platform, data):
        myConnection = mysql.connector.connect(host=dbhostname,port=dbport,user=dbusername,passwd=dbpassword,db=platform+"Discord")
        if myConnection.is_connected():
            cursor = myConnection.cursor()
            findItem = ("PlexUsername" if platform == "Plex" else ("JellyfinID" if platform == "Jellyfin" else "EmbyID"))
            query = "SELECT " + ("DiscordID" if platformOrDiscord == "Discord" else findItem) + " FROM users WHERE " + (findItem if platformOrDiscord == "Discord" else "DiscordID") + " = '" + str(data) + "'"
            cursor.execute(str(query))
            result = cursor.fetchall()
            cursor.close()
            myConnection.close()
            return result
        
    def password(self, length):
        """Generate a random string of letters and digits """
        lettersAndDigits = string.ascii_letters + string.digits
        return ''.join(random.choice(lettersAndDigits) for i in range(length))
    
    def r_post(self, cmd, params):
        return json.loads(requests.post(JELLYFIN_URL + "/" + cmd + "?api_key=" + JELLYFIN_KEY).text)
    
    def r_get(self, cmd, params):
        return json.loads(requests.get(JELLYFIN_URL + "/" + cmd + "?api_key=" + JELLYFIN_KEY).text)
    
    def r_delete(self, cmd, params):
        return json.loads(requests.delete(JELLYFIN_URL + "/" + cmd + "?api_key=" + JELLYFIN_KEY).text)
        
    #def request(self, cmd, params):
    #    return json.loads(requests.get(JELLYFIN_URL + "/" + cmd + "?apikey=" + TAUTULLI_API_KEY + "&" + str(params) + "&cmd=" + str(cmd)).text if params != None else requests.get(TAUTULLI_BASE_URL + "/api/v2?apikey=" + TAUTULLI_API_KEY + "&cmd=" + str(cmd)).text)
    
    @commands.group(aliases=["Crash", "cr", "ch"], pass_context=True)
    async def crash(self, ctx: commands.Context):
        """
        CrashCourse commands
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")
    
    @crash.command(name="invite", aliases=["add","new","join"], pass_context=True)
    @commands.has_role(ADMIN_ROLE_NAME)
    async def crash_add(self, ctx: commands.Context, user: discord.Member, username: str):
        """
        Add a Discord user to Plex, Emby and Jellyfin
        """
        s3 = self.add_to_plex(username, user.id, 's')
        s1 = self.add_to_jellyfin(username, user.id, 's')
        s2 = self.add_to_emby(username, user.id, 's')
        if str(s1).startswith("2") and str(s2).startswith("2") and s3:
            await user.create_dm()
            await user.dm_channel.send("Welcome to " + SERVER_NICKNAME + "!\n" +
                                       "Emby Settings: \n" +
                                       "Hostname: " + EMBY_URL + "\n" +
                                       "Username: " + username + "\n\n" +
                                       "Jellyfin Settings: \n" +
                                       "Hostname: " + JELLYFIN_URL + "\n" +
                                       "Username: " + username + "\n\n" +
                                       "Leave password blank on first login, but please secure your account by setting a password.\n" + 
                                       "Have fun!")
            await ctx.send("You've been added, " + user.mention + "! Please check your direct messages for login information.")
        else:
            await ctx.send("An error occurred while adding " + user.mention)
            
    @crash_add.error
    async def crash_add_error(self, ctx, error):
        await ctx.send("Please mention the Discord user to add to the platforms, as well as their Plex username.")
            
    @crash.command(name="remove", aliases=["delete","rem"], pass_context=True)
    @commands.has_role(ADMIN_ROLE_NAME)
    async def crash_remove(self, ctx: commands.Context, user: discord.Member):
        """
        Delete a Discord user from Plex, Emby and Jellyfin
        """
        s3 = self.delete_from_plex(user.id)
        s1 = self.remove_from_jellyfin(user.id)
        s2 = self.remove_from_emby(user.id)
        await user.remove_roles(discord.utils.get(ctx.message.guild.roles, name=afterApprovedRoleName), reason="Removed from streaming platforms")
        if str(s1).startswith("2") and str(s2).startwith("2") and s3:
            await ctx.send("You've been removed from " + str(SERVER_NICKNAME) + ", " + user.mention + ".")
        elif str(s1).startswith("7") or str(s2).startswith("7"):
            await ctx.send("Not all accounts for " + user.mention + " were successfully removed.")
        elif str(s1).startswith("9") or str(s2).startswith("9"):
            notAllAccounts = ""
            if not s3:
                notAllAccounts = notAllAccounts + "There are no Plex accounts for " + user.mention + ". "
            if str(s1).startswith("9"):
                notAllAccounts = notAllAccounts + "There are no Jellyfin accounts for " + user.mention + ". "
            if str(s2).startswith("9"):
                notAllAccounts = notAllAccounts + "There are no Emby accounts for " + user.mention + ". "
            await ctx.send(user.mention + " was removed from some platforms. " + notAllAccounts)
        else:
            await ctx.send("An error occurred while removing " + user.mention)
            
    @crash_remove.error
    async def crash_remove_error(self, ctx, error):
        await ctx.send("An error occurred. Please mention the Discord user to remove from the platforms.")
        
    @crash.command(name="trial")
    @commands.has_role(ADMIN_ROLE_NAME)
    async def crash_trial(self, ctx: commands.Context, user: discord.Member, username: str):
        """
        Start a trial of Plex, Emby and Jellyfin
        """
        s3 = self.add_to_plex(username, user.id, 't')
        s1 = self.add_to_jellyfin(username, user.id, 't')
        s2 = self.add_to_emby(username, user.id, 't')
        if str(s1).startswith("2") and str(s2).startswith("2") and s3:
            await user.create_dm()
            await user.dm_channel.send("You have been granted a " + str(TRIAL_LENGTH) + "-hour trial to " + SERVER_NICKNAME + "!\n" +
                                       "Emby Settings: \n" +
                                       "Hostname: " + EMBY_URL + "\n" +
                                       "Username: " + username + "\n\n" +
                                       "Jellyfin Settings: \n" +
                                       "Hostname: " + JELLYFIN_URL + "\n" +
                                       "Username: " + username + "\n\n" +
                                       "Leave password blank on first login, but please secure your account by setting a password.\n" + 
                                       "Have fun!")
            await ctx.send("Your trial of " + str(SERVER_NICKNAME) + " has begun, " + user.mention + "! Please check your direct messages for login information.")
        else:
            await ctx.send("An error occurred while starting a trial for " + user.mention)
            
    @crash_trial.error
    async def crash_trial_error(self, ctx, error):
        await ctx.send("Please mention the Discord user to add to the platforms, as well as their Plex username.")
        
    @crash.command(name="prices", aliases=["price","cost"])
    async def crash_prices(self, ctx: commands.Context):
        embed = discord.Embed(title=SERVER_NICKNAME + " Prices")
        for c in PRICES:
            prices = ""
            for p in PRICES[c]:
                prices = prices + p + ": " + PRICES[c][p] + "\n"
            embed.add_field(name=c,value=prices, inline=False)
        embed.add_field(name=PAYMENT_MSG, value='\u200b')
        await ctx.send(embed=embed)
        
    @crash.command(name="pay", aliases=["sub","subscribe"])
    async def crash_pay(self, ctx: commands.Context):
        await ctx.send(PAYMENT_MSG)
            
    def __init__(self, bot):
        self.bot = bot
        print("CrashCourse Manager ready to go.")
