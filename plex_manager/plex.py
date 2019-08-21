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
# (DiscordID BIGINT, PlexUsername 'VARCHAR(100)', PlexEmail 'VARCHAR(320)', ExpirationStamp INT, Note 'VARCHAR(5)')


# Discord-to-Plex database credentials
hostname = os.environ.get('DATABASE_HOST')
port = os.environ.get('DATABASE_PORT')
username = os.environ.get('DATABASE_USER')
password = os.environ.get('DATABASE_PASS')
database = 'PlexDiscord'

# Plex Server settings
PLEX_SERVER_NAME = os.environ.get("PLEX_SERVER_NAME")

# Ombi settings
USE_OMBI = True

# Tautulli settings
USE_TAUTULLI = True

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
# The Discord administrator types "pm add <@DiscordUser> <PlexUsername>".
# The mentioned Discord user will be associated with the corresponding Plex username.
# "pm remove <@DiscordUser>" will remove the mentioned Discord user's Plex access.
#
# True:
# A user posts their Plex username in a Discord channel.
# The "ADMIN_ID" Discord administrator reacts to the message with the "approvedEmojiName" emoji. (Must be that emoji, must be that one Discord administrator)
# The bot then automatically adds the user to Plex and other services.
# This works for regular users, as well as those with the WINNER_ROLE_NAME role. This DOES NOT WORK for those with the TRIAL_ROLE_NAME role
# Users must be the one to post their username, since the bot links the posting user with the corresponding Plex username.
# Removing the emoji will trigger an uninvite.
#
# React-to-add is faster (one-click add, rather than typing), but requires users to post their own username.
# Also, if the bot reboots, it will not see reactions added to messages prior to it coming online (adding/removing reactions to older messages will not trigger the add/remove functions)

approvedEmojiName = "approved"

# Trial settings
TRIAL_ROLE_NAME = "Trial Member"
TRIAL_LENGTH = 24 # hours
TRIAL_INSTRUCTIONS = "Hello, welcome to " + PLEX_SERVER_NAME + "! You have been granted a " + str(TRIAL_LENGTH) + "-hour trial!"
TRIAL_CHECK_FREQUENCY = 15 # minutes
TRIAL_END_NOTIFICATION = "Hello, your " + str(TRIAL_LENGTH) + "-hour trial of " + PLEX_SERVER_NAME + " has ended."

# Winner settings
WINNER_ROLE_NAME = "Winner"
WINNER_THRESHOLD = 2 # hours

# Logging settings
FRIENDLY_LOGGING = False
#FRIENDLY_LOG_CHANNEL_ID = ###########
VERBOSE_LOGGING = False
#VERBOSE_LOG_CHANNEL_ID = ###############



### DO NOT EDIT
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



### Code below ###

class PlexManager(commands.Cog):
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
            #await self.log(str(plexname) + " added to Tautulli.", "v")
        
    async def delete_from_tautulli(self, plexname):
        if USE_TAUTULLI == False:
            pass
        else:
            response = await self.t_request("delete_user","user_id=" + str(plexname))
            #requests.get(TAUTULLI_URL + "delete_user&user_id=" + str(plexname))
            #await self.log(str(plexname) + " removed from Tautulli.", "v")
        
    async def add_to_ombi(self, plexname):
        if USE_OMBI == False:
            pass
        else:
            requests.post(ombi_import,headers=ombi_headers)
            #await self.log(str(plexname) + " added to Ombi.", "v")

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
            #await self.log(str(plexname) + " removed from Ombi.", "v")

    async def add_to_plex(self, plexname):
        plex.myPlexAccount().inviteFriend(user=plexname,server=plex,sections=None, allowSync=False, allowCameraUpload=False, allowChannels=False, filterMovies=None, filterTelevision=None, filterMusic=None)
        #await self.log(str(plexname) + " added to Plex.", "v")
        asyncio.sleep(60)
        await self.add_to_tautulli(plexname)
        await self.add_to_ombi(plexname)
        
    async def delete_from_plex(self, plexname):
        #await self.log("Removing " + plexname + " from Plex.", "v")
        try:
            plex.myPlexAccount().removeFriend(user=plexname)
            #await self.log(str(plexname) + " removed from Plex.", "v")
        except plexapi.exceptions.NotFound:
            print("Not removed.")
            #await self.log(plexname + " not removed because not a current " + PLEX_SERVER_NAME + " user.", "v")
            
    async def check_db(self, data, type):
        conn = mysql.connector.connect(host=hostname,port=port,user=username,passwd=password,db=database)
        response = ""
        if conn.is_connected():
            cur = conn.cursor(buffered=True)
            query = "SELECT * FROM regular_users WHERE " + ("DiscordID" if type == "Discord" else "PlexUsername") + " = " + str(data)
            cur.execute(query)
            for el in cur.fetchone:
                for i in range(0, len(cur.description)):
                    response = response + cur.description[i][0] + " " + el[i] + "\n"
            cur.close()
            conn.close()
            return response

    async def add_user_to_db(self, discordId, plexUsername, note):
        myConnection = mysql.connector.connect(host=hostname,port=port,user=username,passwd=password,db=database)
        if myConnection.is_connected():
            cursor = myConnection.cursor(buffered=True)
            query = ""
            if note == 't':
                query = "INSERT INTO users (DiscordID, PlexUsername, ExpirationStamp, Note) VALUES ('" + str(discordId) + "','" + str(plexUsername) + "','" + str(int(time.time()) + (3600 * TRIAL_LENGTH)) + "','" + str(note) + "')"
            else:
                query = "INSERT INTO users (DiscordID, PlexUsername, Note) VALUES ('" + str(discordId) + "','" + str(plexUsername) + "','" + str(note) + "')"
            cursor.execute(str(query))
            myConnection.commit()
            cursor.close()
            myConnection.close()
        
    async def remove_user_from_db(self, id):
        myConnection = mysql.connector.connect(host=hostname,port=port,user=username,passwd=password,db=database)
        if myConnection.is_connected():
            cursor = myConnection.cursor(buffered=True)
            cursor.execute(str("DELETE FROM users WHERE DiscordID = " + str(id)))
            myConnection.commit()
            cursor.close()
            myConnection.close()
            
    async def find_user_in_db(self, PlexOrDiscord, data):
        myConnection = mysql.connector.connect(host=hostname,port=port,user=username,passwd=password,db=database)
        if myConnection.is_connected():
            cursor = myConnection.cursor()
            query = "SELECT " + ("PlexUsername" if PlexOrDiscord == "Plex" else "DiscordID") + " FROM users WHERE " + ("DiscordID" if PlexOrDiscord == "Plex" else "PlexUsername") + " = '" + str(data) + "'"
            cursor.execute(str(query))
            result = cursor.fetchone()[0]
            cursor.close()
            myConnection.close()
            return result
        
    async def purge_winners(self, ctx):
        try:
            myConnection = mysql.connector.connect(host=hostname,port=port,user=username,passwd=password,db=database)
            monitorlist = []
            if myConnection.is_connected():
                cur = myConnection.cursor()
                cur.execute("SELECT PlexUsername FROM users WHERE Note = 'w'")
                for u in cur:
                    monitorlist.append(u[0])
                cur.close()
                myConnection.close()
                print(monitorlist)
                data = await self.t_request("get_users_table","length=1000")
                removed_list = ""
                for i in data['response']['data']['data']:
                    try:
                        if str(i['friendly_name']) in monitorlist:
                            #print(i['friendly_name'] + " is in the monitor list, checking...")
                            PlexUsername = (await self.t_request("get_user","user_id="+str(i['user_id'])))['response']['data']['username']
                            print(PlexUsername)
                            if i['duration'] is None:
                                #await self.log(str(i['friendly_name']) + " has not played anything. Pruning " + str(i['friendly_name']), "v")
                                mention_id = await self.remove_winner(str(PlexUsername), ctx)
                                removed_list = removed_list + (mention_id if mention_id != None else "")
                            elif i['last_seen'] is None:
                                #await self.log(str(i['friendly_name']) + " has never been seen. Pruning " + str(i['friendly_name']), "v")
                                mention_id = await self.remove_winner(str(PlexUsername),ctx)
                                removed_list = removed_list + (mention_id if mention_id != None else "")
                            elif i['duration']/3600 < WINNER_THRESHOLD:
                                #await self.log(str(i['friendly_name']) + " has watched less than " + str(WINNER_THRESHOLD) + " hours of content. Pruning " + str(i['friendly_name']), "v")
                                mention_id = await self.remove_winner(str(PlexUsername),ctx)
                                removed_list = removed_list + (mention_id if mention_id != None else "")
                            elif time.time()-i['last_seen'] > 1209600:
                                #await self.log(str(i['friendly_name']) + " has not been seen in two weeks. Pruning " + str(i['friendly_name']), "v")
                                mention_id = await self.remove_winner(str(PlexUsername),ctx)
                                removed_list = removed_list + (mention_id if mention_id != None else "")
                            else:
                                print(PlexUsername + " has met the requirements")
                                #await self.log(str(i['friendly_name']) + " has met the requirements. Not pruned.", "v")
                    except Exception as e:
                        print(e)
                        #await self.log(str(e), "v")
                if removed_list != "":
                    #print(removed_list)
                    await ctx.send(removed_list + "You have been removed as a Winner due to inactivity.")
                else:
                    await ctx.send("No winners purged.")
        except Exception as e:
            print(e)
            await ctx.send("Something went wrong. Please try again later.")
        
        
    ##### MAKE EDITS WHEN DEPLOYING #####
    async def remove_winner(self, username,ctx):
        #self.delete_from_plex(username)
        id = await self.find_user_in_db("Discord", username)
        if id != None:
            user = ctx.message.server.get_member(id)
            #await user.create_dm()
            #await user.dm_channel.send("You have been removed from " + str(PLEX_SERVER_NAME) + " due to inactivity.")
            #await user.remove_roles(discord.utils.get(self.bot.get_guild(SERVER_ID).roles, name="Winner"), reason="Inactive winner")
            #await self.remove_user_from_db(id)
            return "<@" + id + ">, "
        else:
            #print("Error trying to remove Winner role from " + str(username))
            #await self.log("Error trying to remove Winner role from " + str(username), "v")
            return None
    
    async def remove_nonsub(self, memberID):
        if memberID not in exemptsubs:
            plexUsername = await self.find_user_in_db("Plex", memberID)
            self.delete_from_plex(plexname)
            self.delete_from_ombi(plexname)
    
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
            query = "SELECT PlexUsername, DiscordID FROM users WHERE ExpirationStamp<=" + str(int(time.time())) + " AND Note = 't'";
            cur.execute(str(query))
            trial_role = discord.utils.get(self.bot.get_guild(SERVER_ID).roles, name=TRIAL_ROLE_NAME)
            for u in cur:
                await self.delete_from_plex(u[0])
                await self.delete_from_tautulli(u[0])
                user = self.bot.get_guild(SERVER_ID).get_member(u[1])
                await user.create_dm()
                await user.dm_channel.send(TRIAL_END_NOTIFICATION)
                await user.remove_roles(trial_role, reason="Trial has ended.")
                await self.remove_user_from_db(u[1])
            cur.close()
            myConnection.close()
        
    @commands.group(name="pm",aliases=["PM","PlexMan","plexman"],pass_context=True)
    @commands.has_role(ADMIN_ROLE_NAME)
    async def pm(self, ctx: commands.Context):
        """
        Plex admin commands
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")
        
    @pm.command(name="purge", pass_context=True)
    @commands.has_role(ADMIN_ROLE_NAME)
    async def pm_purge(self, ctx: commands.Context):
        """
        Remove inactive winners
        """
        await self.purge_winners(ctx)
        
    @pm.command(name="count")
    @commands.has_role(ADMIN_ROLE_NAME)
    async def pm_count(self, ctx: commands.Context):
        """
        Check Plex share count
        """
        count = 0
        for u in plex.myPlexAccount().users():
            for s in u.servers:
                if s.name == "PLEX_SERVER_NAME":
                        count+=1
        await ctx.send(PLEX_SERVER_NAME + " has " + str(count) + " subscribers")
        
    @pm_count.error
    async def pm_count_error(self, ctx, error):
        await ctx.send("Something went wrong. Please try again later.")
        
    @pm.command(name="add",alias=["invite","new"])
    @commands.has_role(ADMIN_ROLE_NAME)
    async def pm_add(self, ctx: commands.Context, user: discord.Member, PlexUsername: str):
        """
        Add a Discord user to Plex
        """
        if REACT_TO_ADD == False:
            await ctx.send('Adding ' + PlexUsername + ' to Plex. Please wait about 60 seconds...')
            try:
                winner_role = discord.utils.get(ctx.message.guild.roles, name=WINNER_ROLE_NAME)
                await self.add_to_plex(PlexUsername)
                if winner_role in user.roles:
                    await self.add_user_to_db(user.id, PlexUsername, 'w')
                else:
                    await self.add_user_to_db(user.id, PlexUsername, 's')
                #await self.log("Discord user " + user.name + " (ID: " + str(user.id) + ") is Plex user " + PlexUsername, "v")
                role = discord.utils.get(ctx.message.guild.roles, name=afterApprovedRoleName)
                await user.add_roles(role, reason="Access membership channels")
                #await self.log("Added " + afterApprovedRoleName + " role to " + str(user.name), "v")
                await ctx.send(user.mention + " You've been invited, " + PlexUsername + ". Welcome to " + PLEX_SERVER_NAME + "!")
            except plexapi.exceptions.BadRequest:
                await ctx.send(PlexUsername + " is not a valid Plex username.")
        else:
            await ctx.send('This function is disabled. Please react to usernames to add to Plex.')
            
    @pm_add.error
    async def pm_add_error(self, ctx, error):
        await ctx.send("Please mention the Discord user to add to Plex, as well as their Plex username.")
            
    @pm.command(name="remove",alias=["uninvite","delete","rem"])
    @commands.has_role(ADMIN_ROLE_NAME)
    async def pm_remove(self, ctx: commands.Context, user: discord.Member):
        """
        Remove a Discord user from Plex
        """
        if REACT_TO_ADD == False:
            plexUsername = await self.find_user_in_db("Plex",user.id)
            await self.delete_from_plex(plexUsername)
            await remove_user_from_db(user.id)
            role = discord.utils.get(ctx.message.guild.roles, name=afterApprovedRoleName)
            await user.remove_roles(role, reason="Removed from Plex")
            await ctx.send("You've been removed from " + PLEX_SERVER_NAME + ", " + user.mention + ".")
        else:
            await ctx.send('This function is disabled. Please remove a reaction from usernames to remove from Plex.')
    
    @pm_remove.error
    async def pm_remove_error(self, ctx, error):
        await ctx.send("Please mention the Discord user to remove from Plex.")
        
    @pm.command(name="trial")
    @commands.has_role(ADMIN_ROLE_NAME)
    async def pm_trial(self, ctx: commands.Context, user: discord.Member, PlexUsername: str):
        await ctx.send('Starting ' + PLEX_SERVER_NAME + ' trial for ' + PlexUsername + '. Please wait about 60 seconds...')
        try:
            plex.myPlexAccount().inviteFriend(user=PlexUsername,server=plex,sections=None, allowSync=False, allowCameraUpload=False, allowChannels=False, filterMovies=None, filterTelevision=None, filterMusic=None)
            asyncio.sleep(60)
            await self.add_to_tautulli(PlexUsername)
            await self.add_user_to_db(user.id, PlexUsername, 't')
            role = discord.utils.get(ctx.message.guild.roles, name=TRIAL_ROLE_NAME)
            await user.add_roles(role, reason="Trial started.")
            await user.create_dm()
            await user.dm_channel.send(TRIAL_INSTRUCTIONS)
            await ctx.send(user.mention + ", your trial has begun. Please check your Direct Messages for details.")
        except plexapi.exceptions.BadRequest:
            await ctx.send(PlexUsername + " is not a valid Plex username.")
            
    @pm_trial.error
    async def pm_trial_error(self, ctx, error):
        await ctx.send("Please mention the Discord user to add to Plex, as well as their Plex username.")
            
        
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if (REACT_TO_ADD) and (reaction.emoji.name == approvedEmojiName) and (user.id in ADMIN_ID): #Add user to Plex and Tautulli
            plexname = reaction.message.content.strip() #Only include username, nothing else
            #await self.log("Adding " + str(plexname), "v")
            await reaction.message.channel.send("Adding " + plexname + ". Please wait about 60 seconds...")
            try:
                winner_role = discord.utils.get(reaction.message.guild.roles, name=WINNER_ROLE_NAME)
                if winner_role in reaction.message.author.roles:
                    f=open(WINNER_FILE,"a")
                    f.write(str(plexname)+",")
                    f.close()
                await self.add_to_plex(plexname)
                if winner_role in reaction.message.author.roles:
                    await self.add_user_to_db(reaction.message.author.id, plexname, 'w')
                else:
                    await self.add_user_to_db(reaction.message.author.id, plexname, 's')
                #await self.log("Discord user " + reaction.message.author.name + " (ID: " + str(reaction.message.author.id) + ") is Plex user " + plexname, "v")
                member = reaction.message.author
                role = discord.utils.get(reaction.message.guild.roles, name=afterApprovedRoleName)
                await member.add_roles(role, reason="Access membership channels")
                #await self.log("Added " + afterApprovedRoleName + " role to " + str(member.name), "v")
                await reaction.message.channel.send(member.mention + " You've been invited, " + plexname + ". Welcome to " + PLEX_SERVER_NAME + "!")
            except plexapi.exceptions.BadRequest:
                await reaction.message.channel.send(reaction.message.author.mention + ", " + plexname + " is not a valid Plex username.")
                #await self.log(str(plexname) + " is not a valid Plex username.", "v")

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        if (REACT_TO_ADD) and (reaction.emoji.name == approvedEmojiName) and (user.name in ADMIN_USERNAME): #Listen for users removed
            plexname = reaction.message.content.strip() #Only include username, nothing else
            await self.delete_from_plex(plexname)
            await reaction.message.channel.send(reaction.message.author.mention + " (" + plexname + "), you have been removed from " + PLEX_SERVER_NAME + ". To appeal this removal, please send a Direct Message to <@" + ADMIN_ID + ">")

    def __init__(self, bot):
        self.bot = bot
        print("Plex Manager ready to go.")
