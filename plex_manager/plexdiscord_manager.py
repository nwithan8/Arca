import discord
from discord.ext import commands, tasks
import requests
import asyncio
import datetime
import time
from plexapi.server import PlexServer
import plexapi
from plexapi.myplex import MyPlexAccount
import mysql.connector
import urllib
import json
import re
from discord.ext import commands
import sys, traceback, os

# Database Schema:
# PlexDiscord.users
# (DiscordID BIGINT, PlexUsername 'VARCHAR(100)', PlexEmail 'VARCHAR(320)', ExpirationStamp INT)


#Discord-to-Plex database credentials
hostname = 'localhost'
username = 'DiscordBot'
password = 'DiscordBot'
database = 'PlexDiscord'

#Plex Server settings
PLEX_SERVER_NAME = os.environ.get("PLEX_SERVER_NAME")

#Ombi settings
USE_OMBI = True

#Tautulli settings
USE_TAUTULLI = True

#Discord settings
SERVER_ID = #######
ADMIN_USERNAME = 'username'
ADMIN_ID = #######
FRIENDLY_LOGGING = True
FRIENDLY_LOG_CHANNEL_ID = ###########
VERBOSE_LOGGING = True
VERBOSE_LOG_CHANNEL_ID = ###############
approvedEmojiName = "approved"
afterApprovedRoleName = "Invited"
stopEmojiName = "stop"
stop_message = "Please contact @" + ADMIN_USERNAME + "in a private message on Discord."
subRoles = ["Monthly Subscriber","Yearly Subscriber", "Winner", "Bot"] # Exempt from removal
exemptsubs = [############] # Discord IDs for users who are exempt from subscriber checks/deletion
SUB_CHECK_TIME = 7 #days
WINNER_THRESHOLD = 2 #hours
WINNER_FILE = "monitorwinners.txt" # Needs to be in the root of your bot folder (same folder as bot.py)

### DO NOT EDIT
plex = PlexServer(os.environ.get('PLEX_URL'), os.environ.get('PLEX_TOKEN'))
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
TAUTULLI_URL = os.environ.get('TAUTULLI_URL') + "/api/v2?apikey=" + os.environ.get('TAUTULLI_KEY') + "&cmd="



### Code below ###

class PlexDiscord_Manager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
                
    async def t_request(self, cmd, params):
        return json.loads(requests.get(os.environ.get('TAUTULLI_URL') + "/api/v2?apikey=" + os.environ.get('TAUTULLI_KEY') + "&cmd=" + str(cmd) + (("&" + str(params)) if params != None else "")).text)
    
    async def log(self, log_message, logType):
        if VERBOSE_LOGGING == True:
            print(log_message)
            vl_channel = self.bot.get_channel(VERBOSE_LOG_CHANNEL_ID)
            await vl_channel.send(log_message)
            #await vlogChannel.send(log_message)
        if (FRIENDLY_LOGGING == True) and (logType == "f"):
            fl_channel = self.bot.get_channel(FRIENDLY_LOG_CHANNEL_ID)
            await fl_channel.send(log_message)
            #await flogChannel.send(log_message)
    
    async def add_to_tautulli(self, plexname):
        if USE_TAUTULLI == False:
            pass
        else:
            response = await self.t_request("refresh_users_list",None)
            await self.log(str(plexname) + " added to Tautulli.", "v")
        
    async def delete_from_tautulli(self, plexname):
        if USE_TAUTULLI == False:
            pass
        else:
            response = await self.t_request("delete_user","user_id=" + str(plexname))
            #requests.get(TAUTULLI_URL + "delete_user&user_id=" + str(plexname))
            await self.log(str(plexname) + " removed from Tautulli.", "v")
        
    async def add_to_ombi(self, plexname):
        if USE_OMBI == False:
            pass
        else:
            requests.post(ombi_import,headers=ombi_headers)
            await self.log(str(plexname) + " added to Ombi.", "v")

    async def delete_from_ombi(self, plexname):
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
            await self.log(str(plexname) + " removed from Ombi.", "v")

    async def add_to_plex(self, plexname):
        plex.myPlexAccount().inviteFriend(user=plexname,server=plex,sections=None, allowSync=False, allowCameraUpload=False, allowChannels=False, filterMovies=None, filterTelevision=None, filterMusic=None)
        await self.log(str(plexname) + " added to Plex.", "v")
        asyncio.sleep(60)
        await self.add_to_tautulli(plexname)
        await self.add_to_ombi(plexname)
        
    async def delete_from_plex(self, plexname):
        await self.log("Removing " + plexname + " from Plex.", "v")
        try:
            plex.myPlexAccount().removeFriend(user=plexname)
            await self.log(str(plexname) + " removed from Plex.", "v")
        except plexapi.exceptions.NotFound:
            print("Not removed.")
            await self.log(plexname + " not removed because not a current " + PLEX_SERVER_NAME + " user.", "v")
            
    async def check_db(self, data,type):
        conn = mysql.connector.connect(host=hostname,user=username,passwd=password,db=database)
        response = ""
        if conn.is_connected():
            await self.log("Connected to database for manual search.","v")
            cur = conn.cursor(buffered=True)
            query = "SELECT * FROM regular_users WHERE " + ("DiscordID" if type == "Discord" else "PlexUsername") + " = " + str(data)
            cur.execute(query)
            for el in cur.fetchone:
                for i in range(0, len(cur.description)):
                    response = response + cur.description[i][0] + " " + el[i] + "\n"
            cur.close()
            conn.close()
            await self.log("Connection to database for manual search closed.","v")
            return response

    async def add_to_regular_db(self, id, name):
        myConnection = mysql.connector.connect(host=hostname,user=username,passwd=password,db=database)
        if myConnection.is_connected():
            await self.log("Connected to database.", "v")
            cursor = myConnection.cursor(buffered=True)
            query = "INSERT INTO users (DiscordID, PlexUsername) VALUES ('" + str(id) + "','" + str(name) + "')"
            cursor.execute(str(query))
            await self.log(str(id) + "/" + str(name) + " added to DB.", "v")
            myConnection.commit()
            await self.log("Database changes committed.", "v")
            cursor.close()
            myConnection.close()
            await self.log("Database connection closed.", "v")
        
    async def remove_from_db(self, whichDatabase, id):
        myConnection = mysql.connector.connect(host=hostname,user=username,passwd=password,db=database)
        if myConnection.is_connected():
            await self.log("Connected to database.", "v")
            cursor = myConnection.cursor(buffered=True)
            cursor.execute(str("DELETE FROM " + str(whichDatabase) + "_users WHERE DiscordID = " + str(id)))
            myConnection.commit()
            cursor.close()
            myConnection.close()
            await self.log(str(id) + " removed from " + whichDatabase + " users.", "v")
            await self.log("Database connection closed.", "v")
            
    async def find_in_db(self, PlexOrDiscord, data):
        myConnection = mysql.connector.connect(host=hostname,user=username,passwd=password,db=database)
        result = None
        if myConnection.is_connected():
            cursor = myConnection.cursor(buffered=True)
            query = "SELECT " + ("PlexUsername" if PlexOrDiscord == "Plex" else "DiscordID") + " FROM users WHERE " + ("DiscordID" if PlexOrDiscord == "Plex" else "PlexUsername") + " = '" + str(data) + "'"
            cursor.execute(str(query))
            await self.log("Database query executed.", "v")
            if cursor.fetchone():
                result = cursor.fetchone()[0]
            cursor.close()
            myConnection.close()
            return result
        
    async def purge_winners(self, ctx):
        with open(WINNER_FILE,"r") as f:
            monitorlist=f.read().split(",")
            data = await self.t_request("get_users_table","length=1000")
            removed_list = ""
            for i in data['response']['data']['data']:
                try:
                    if str(i['friendly_name']) in monitorlist:
                        #print(i['friendly_name'] + " is in the monitor list, checking...")
                        username = (await self.t_request("get_user","user_id="+str(i['user_id'])))['response']['data']['username']
                        print(username)
                        if i['duration'] is None:
                            await self.log(str(i['friendly_name']) + " has not played anything. Pruning " + str(i['friendly_name']), "v")
                            mention_id = await self.remove_winner(str(username), ctx)
                            removed_list = removed_list + (mention_id if mention_id != None else "")
                        elif i['last_seen'] is None:
                            await self.log(str(i['friendly_name']) + " has never been seen. Pruning " + str(i['friendly_name']), "v")
                            mention_id = await self.remove_winner(str(username),ctx)
                            removed_list = removed_list + (mention_id if mention_id != None else "")
                        elif i['duration']/3600 < WINNER_THRESHOLD:
                            await self.log(str(i['friendly_name']) + " has watched less than " + str(WINNER_THRESHOLD) + " hours of content. Pruning " + str(i['friendly_name']), "v")
                            mention_id = await self.remove_winner(str(username),ctx)
                            removed_list = removed_list + (mention_id if mention_id != None else "")
                        elif time.time()-i['last_seen'] > 1209600:
                            await self.log(str(i['friendly_name']) + " has not been seen in two weeks. Pruning " + str(i['friendly_name']), "v")
                            mention_id = await self.remove_winner(str(username),ctx)
                            removed_list = removed_list + (mention_id if mention_id != None else "")
                        else:
                            await self.log(str(i['friendly_name']) + " has met the requirements. Not pruned.", "v")
                except Exception as e:
                    await self.log(str(e), "v")
            if removed_list != "":
                await ctx.send(removed_list + "You have been removed as a Winner due to inactivity.")
            else:
                await ctx.send("No winners purged.")
            f.close()
        
        
    ##### MAKE EDITS WHEN DEPLOYING #####
    async def remove_winner(self, username,ctx):
        #self.delete_from_plex(username)
        id = await self.find_in_db("Discord",username)
        if id != None:
            user = ctx.message.server.get_member(id)
            user.create_dm()
            #user.dm_channel.send("You have been removed from " + str(PLEX_SERVER_NAME) + " due to inactivity.")
            #user.remove_roles(discord.utils.get(self.bot.get_guild(SERVER_ID).roles, name="Winner"), reason="Inactive winner")
            return "<@" + id + "> "
        else:
            #print("Error trying to remove Winner role from " + str(username))
            await self.log("Error trying to remove Winner role from " + str(username), "v")
            return None
    
    async def remove_nonsub(self, member):
        if member.id not in exemptsubs:
            myConnection = mysql.connector.connect(host=hostname,user=username,passwd=password,db=database)
            if myConnection.is_connected():
                await self.log("Connected to database.", "v")
                cur = myConnection.cursor(buffered=True)
                query = "SELECT PlexUsername FROM users WHERE DiscordID = '" + str(member.id) + "'"
                cur.execute(str(query))
                plexname = ""
                if cur.fetchone():
                    plexname = cur.fetchone()[0]
                    self.delete_from_plex(plexname) #CHANGE THIS WHEN GOING LIVE WITH SUBS
                    await self.log(member.name + " (" + plexname + " on Plex) deleted from Plex.", "v")
                    self.delete_ombi_user(plexname) #CHANGE THIS WHEN GOING LIVE WITH SUBS
                else:
                    await self.log(str(member.id) + " (" + str(member.name) + ") not found in database.", "v")
                cur.close()
                myConnection.close()
                await self.log("Database connection closed.", "v")
    
    @tasks.loop(seconds=SUB_CHECK_TIME*(3600*24))
    async def check_subs(self):
        current_time = str(int(time.time()))
        myConnection = mysql.connector.connect(host=hostname,user=username,passwd=password,db=database)
        await self.log("Checking non-subscribers.", "v")
        cur = myConnection.cursor(buffered=True)
        query = "SELECT * FROM users"
        cur.execute(str(query))
        #await self.log("Database preview:\n" + str(cur.fetchall()))
        exemptRoles = []
        allRoles = self.bot.get_guild(SERVER_ID).roles
        for r in allRoles:
            if r.name in subRoles:
                exemptRoles.append(r)
        for member in self.bot.get_guild(SERVER_ID).members:
            if not any(x in member.roles for x in exemptRoles):
                await self.remove_nonsub(member)
        myConnection.close()
        
    @commands.Cog.listener()
    async def on_ready(self):
        #self.getLibraries.start()
        await self.log("PlexDiscord Manager ready.", "f")
        
    @commands.group(name="pdm",aliases=["PDM"],pass_context=True)
    @commands.has_role("Admin")
    async def bbm(self, ctx: commands.Context):
        """
        BigBox Media admin commands
        """
        if ctx.invoked_subcommand is None:
            pass
        
    @bbm.command(name="purge", pass_context=True)
    @commands.has_role("Admin")
    async def bmm_purge(self, ctx: commands.Context):
        """
        Remove inactive winners
        """
        await self.purge_winners(ctx)
        
    @bbm.command(name="ping")
    async def bbm_ping(self, ctx: commands.Context):
        """
        Check BBM Manager is working
        """
        await ctx.send("pong")
        
    @bbm.command(name="count")
    @commands.has_role("Admin")
    async def bbm_count(self, ctx: commands.Context):
        """
        Check subscriber count
        """
        count = 0
        for u in plex.myPlexAccount().users():
            for s in u.servers:
                if s.name == "PLEX_SERVER_NAME":
                        count+=1
        await ctx.send(PLEX_SERVER_NAME + " has " + str(count) + " subscribers")
        
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if reaction.emoji.name == approvedEmojiName and user.name in ADMIN_USERNAME: #Add user to Plex and Tautulli
            plexname = reaction.message.content.strip() #Only include username, nothing else
            await self.log("Adding " + str(plexname), "v")
            await reaction.message.channel.send("Adding " + plexname + ". Please wait about 60 seconds...")
            try:
                winner_role = discord.utils.get(reaction.message.guild.roles, name="Winner")
                if winner_role in reaction.message.author.roles:
                    f=open(WINNER_FILE,"a")
                    f.write(str(plexname)+",")
                    f.close()
                await self.add_to_plex(plexname)
                await self.add_to_regular_db(reaction.message.author.id, plexname)
                await self.log("Discord user " + reaction.message.author.name + " (ID: " + str(reaction.message.author.id) + ") is Plex user " + plexname, "v")
                member = reaction.message.author
                role = discord.utils.get(reaction.message.guild.roles, name=afterApprovedRoleName)
                await member.add_roles(role, reason="Access membership channels")
                await self.log("Added " + afterApprovedRoleName + " role to " + str(member.name), "v")
                await reaction.message.channel.send(member.mention + " You've been invited, " + plexname + ". Welcome to " + DISCORD_SERVER_NAME + "!")
            except plexapi.exceptions.BadRequest:
                await reaction.message.channel.send(reaction.message.author.mention + ", " + plexname + " is not a valid Plex username.")
                await self.log(str(plexname) + " is not a valid Plex username.", "v")

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        if reaction.emoji.name == approvedEmojiName and user.name in ADMIN_USERNAME: #Listen for users removed
            plexname = reaction.message.content.strip() #Only include username, nothing else
            await self.delete_from_plex(plexname)
            await reaction.message.channel.send(reaction.message.author.mention + " (" + plexname + "), you have been removed from " + DISCORD_SERVER_NAME + ". To appeal this removal, please send a Direct Message to <@" + ADMIN_ID + ">")

def setup(bot):
    bot.add_cog(PlexDiscord_Manager(bot))
