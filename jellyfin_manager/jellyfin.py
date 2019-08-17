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


#Discord-to-Jellyfin database credentials
hostname = 'localhost'
username = 'DiscordBot'
password = 'DiscordBot'
database = 'JellyfinDiscord'

'''
Database schema:

JellyDiscord.users
(DiscordID BIGINT, JellyfinUsername 'VARCHAR(100)', JellyfinID 'VARCHAR(100)')
'''

JELLYFIN_URL = os.environ.get('JELLYFIN_URL')
JELLYFIN_KEY = os.environ.get('JELLYFIN_KEY')
SERVER_NICKNAME = os.environ.get('JELLYFIN_SERVER_NAME')

class Jellyfin(commands.Cog):
    def check_db(self, data, type):
        conn = mysql.connector.connect(host=hostname,user=username,passwd=password,db=database)
        response = ""
        if conn.is_connected():
            cur = conn.cursor(buffered=True)
            query = "SELECT * FROM regular_users WHERE " + ("DiscordID" if type == "Discord" else "JellyfinUsername") + " = " + str(data)
            cur.execute(query)
            for el in cur.fetchone:
                for i in range(0, len(cur.description)):
                    response = response + cur.description[i][0] + " " + el[i] + "\n"
            cur.close()
            conn.close()
            return response

    def add_user_to_db(self, discordId, jellyfinUsername, jellyfinId):
        myConnection = mysql.connector.connect(host=hostname,user=username,passwd=password,db=database)
        if myConnection.is_connected():
            cursor = myConnection.cursor(buffered=True)
            query = "INSERT INTO users (DiscordID, JellyfinUsername, JellyfinID) VALUES ('" + str(discordId) + "','" + str(jellyfinUsername) + "','" + str(jellyfinId) + "')"
            cursor.execute(str(query))
            myConnection.commit()
            cursor.close()
            myConnection.close()
        
    def remove_user_from_db(self, id):
        myConnection = mysql.connector.connect(host=hostname,user=username,passwd=password,db=database)
        if myConnection.is_connected():
            cursor = myConnection.cursor(buffered=True)
            cursor.execute(str("DELETE FROM users WHERE DiscordID = " + str(id)))
            myConnection.commit()
            cursor.close()
            myConnection.close()
            
    def find_user_in_db(self, JellyfinOrDiscord, data):
        myConnection = mysql.connector.connect(host=hostname,user=username,passwd=password,db=database)
        if myConnection.is_connected():
            cursor = myConnection.cursor()
            query = "SELECT " + ("JellyfinID" if JellyfinOrDiscord == "Jellyfin" else "DiscordID") + " FROM users WHERE " + ("DiscordID" if JellyfinOrDiscord == "Jellyfin" else "JellyfinID") + " = '" + str(data) + "'"
            cursor.execute(str(query))
            result = cursor.fetchone()[0]
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
    
    def new_user(self, username, discordId):
        payload = {
            "Name": username
        }
        r = json.loads(requests.post(JELLYFIN_URL + "/emby/emby/Users/New?api_key=" + JELLYFIN_KEY, json=payload).text)
        #p = self.password(length=10)
        #print(p)
        Id = r['Id']
        #r = requests.post(JELLYFIN_URL + "/emby/emby/Users/" + str(Id) + "/Password?api_key=" + JELLYFIN_KEY, json=payload) # CANNOT CURRENTLY SET PASSWORD FOR NEW USER
        #print(r.status_code)
        self.add_user_to_db(discordId, username, Id)
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
        return requests.post(JELLYFIN_URL + "/emby/emby/Users/" + str(Id) + "/Policy?api_key=" + JELLYFIN_KEY, json=payload).status_code
        
    #def request(self, cmd, params):
    #    return json.loads(requests.get(JELLYFIN_URL + "/" + cmd + "?apikey=" + TAUTULLI_API_KEY + "&" + str(params) + "&cmd=" + str(cmd)).text if params != None else requests.get(TAUTULLI_BASE_URL + "/api/v2?apikey=" + TAUTULLI_API_KEY + "&cmd=" + str(cmd)).text)
    
    @commands.group(aliases=["Jelly, jelly JF, jf"], pass_context=True)
    @commands.has_role("Admin")
    async def jellyfin(self, ctx: commands.Context):
        """
        Jellyfin Media Server commands
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")
    
    @jellyfin.command(name="add", aliases=["new","join"], pass_context=True)
    async def jellyfin_add(self, ctx: commands.Context, user: discord.Member, username: str):
        """
        Add a Discord user to Jellyfin
        """
        s = self.new_user(username, user.id)
        if str(s).startswith("2"):
            await user.create_dm()
            await user.dm_channel.send("You have been added to " + SERVER_NICKNAME + "!\n" +
                                       "Hostname: " + JELLYFIN_URL + "\n" +
                                       "Username: " + username + "\n" +
                                       "Leave password blank on first login, but please secure your account by setting a password.\n" + 
                                       "Have fun!")
            await ctx.send("You've been added, " + user.mention + "! Please check your direct messages for login information.")
        else:
            await ctx.send("An error occurred while adding " + user.mention)
            
    @jellyfin_add.error
    async def jellyfin_add_error(self, ctx, error):
        await ctx.send("Please mention the Discord user to add to Jellyfin, as well as their Jellyfin username.")
            
    @jellyfin.command(name="remove", aliases=["delete","rem"], pass_context=True)
    async def jellyfin_remove(self, ctx: commands.Context, user: discord.Member):
        """
        Delete a Discord user from Jellyfin
        """
        jellyfinId = self.find_user_in_db("Jellyfin", user.id)
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
        #s = requests.post(JELLYFIN_URL + "/emby/emby/Users/" + str(jellyfinId) + "/Policy?api_key=" + JELLYFIN_KEY, json=payload).status_code
        # Doesn't delete user, instead makes deactive.
        # Delete function not documented in Jellyfin API, but exists in old Emby API and still works
        s = requests.delete(JELLYFIN_URL + "/emby/emby/Users/" + str(jellyfinId) + "?api_key=" + JELLYFIN_KEY).status_code
        self.remove_user_from_db(user.id)
        if str(s).startswith("2"):
            await ctx.send("You've been removed from " + SERVER_NICKNAME + ", " + user.mention + ".")
        else:
            await ctx.send("An error occurred while removing " + user.mention)
            
    @jellyfin_remove.error
    async def jellyfin_remove_error(self, ctx, error):
        await ctx.send("Please mention the Discord user to remove from Jellyfin.")
            
    @jellyfin.command(name="count", aliases=["subs","number"], pass_context=True)
    async def jellyfin_count(self, ctx: commands.Context):
        """
        Get the number of enabled Jellyfin users
        """
        count = len(json.loads(requests.get(JELLYFIN_URL + "/emby/emby/Users?api_key=" + JELLYFIN_KEY).text))
        if count > 0:
            await ctx.send(SERVER_NICKNAME + " has " + str(count) + " users.")
        else:
            await ctx.send("An error occurred.")
            
    @jellyfin_count.error
    async def jellyfin_count_error(self, ctx, error):
        await ctx.send("Something went wrong. Please try again later.")
            
    def __init__(self, bot):
        self.bot = bot
        print("Jellyfin ready to go.")
