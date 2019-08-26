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
dbhostname = os.environ.get('DATABASE_HOST')
dbport = os.environ.get('DATABASE_PORT')
dbusername = os.environ.get('DATABASE_USER')
dbpassword = os.environ.get('DATABASE_PASS')
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
                
    def t_request(self, cmd, params):
        return json.loads(requests.get(os.environ.get('TAUTULLI_URL') + "/api/v2?apikey=" + os.environ.get('TAUTULLI_KEY') + "&cmd=" + str(cmd) + (("&" + str(params)) if params != None else "")).text)
    
    def add_to_tautulli(self, plexname):
        if USE_TAUTULLI == False:
            pass
        else:
            response = self.t_request("refresh_users_list",None)
        
    def delete_from_tautulli(self, plexname):
        if not USE_TAUTULLI:
            pass
        else:
            response = self.t_request("delete_user","user_id=" + str(plexname))
            #requests.get(TAUTULLI_URL + "delete_user&user_id=" + str(plexname))
        
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

    async def add_to_plex(self, plexname, discordId, note):
        try:
            plex.myPlexAccount().inviteFriend(user=plexname,server=plex,sections=None, allowSync=False, allowCameraUpload=False, allowChannels=False, filterMovies=None, filterTelevision=None, filterMusic=None)
            self.add_user_to_db(discordId, plexname, note)
            await asyncio.sleep(60)
            self.add_to_tautulli(plexname)
            if note != 't': # Trial members do not have access to Ombi
                self.add_to_ombi(plexname)
            return True
        except Exception as e:
            print(e)
            return False
        
    def delete_from_plex(self, id):
        try:
            plexname, note = self.find_user_in_db("Plex", id)
            plex.myPlexAccount().removeFriend(user=plexname)
            if note != 't':
                self.delete_from_ombi(plexname) # Error if trying to remove trial user that doesn't exist in Ombi?
            self.delete_from_tautulli(plexname)
            self.remove_user_from_db(id)
            return True
        except plexapi.exceptions.NotFound:
            print("Not found")
            return False
        
    def describe_table(self, table):
        conn = mysql.connector.connect(host=dbhostname,port=dbport,user=dbusername,passwd=dbpassword,db=database)
        response = ""
        if conn.is_connected():
            cur = conn.cursor(buffered=True)
            cur.execute("DESCRIBE " + str(table))
            response = cur.fetchall()
            cur.close()
            conn.close()
            return response
            
    def pull_user_from_db(self, type, data):
        conn = mysql.connector.connect(host=dbhostname,port=dbport,user=dbusername,passwd=dbpassword,db=database)
        response = ""
        if conn.is_connected():
            cur = conn.cursor(buffered=True)
            query = "SELECT * FROM users WHERE " + ("DiscordID" if type == "Discord" else "PlexUsername") + " = '" + str(data) + "'"
            cur.execute(query)
            response = cur.fetchone()
            cur.close()
            conn.close()
            return response

    def add_user_to_db(self, discordId, plexUsername, note):
        myConnection = mysql.connector.connect(host=dbhostname,port=dbport,user=dbusername,passwd=dbpassword,db=database)
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
            
    def remove_user_from_db(self, id):
        myConnection = mysql.connector.connect(host=dbhostname,port=dbport,user=dbusername,passwd=dbpassword,db=database)
        if myConnection.is_connected():
            cursor = myConnection.cursor(buffered=True)
            cursor.execute(str("DELETE FROM users WHERE DiscordID = " + str(id)))
            myConnection.commit()
            cursor.close()
            myConnection.close()
            
    def find_user_in_db(self, PlexOrDiscord, data):
        myConnection = mysql.connector.connect(host=dbhostname,port=dbport,user=dbusername,passwd=dbpassword,db=database)
        r1 = ""
        r2 = ""
        if myConnection.is_connected():
            cursor = myConnection.cursor()
            query = "SELECT " + ("PlexUsername, Note" if PlexOrDiscord == "Plex" else "DiscordID") + " FROM users WHERE " + ("DiscordID" if PlexOrDiscord == "Plex" else "PlexUsername") + " = '" + str(data) + "'"
            cursor.execute(str(query))
            results = cursor.fetchone()
            if PlexOrDiscord == "Plex":
                return results[0], results[1]
            else:
                return results[0]
            cursor.close()
            myConnection.close()
        
    async def purge_winners(self, ctx):
        try:
            myConnection = mysql.connector.connect(host=dbhostname,port=dbport,user=dbusername,passwd=dbpassword,db=database)
            monitorlist = []
            if myConnection.is_connected():
                cur = myConnection.cursor()
                cur.execute("SELECT PlexUsername FROM users WHERE Note = 'w'")
                for u in cur.fetchall():
                    monitorlist.append(u[0])
                cur.close()
                myConnection.close()
                print("Winners: ")
                print(monitorlist)
                data = self.t_request("get_users_table","length=1000")
                removed_list = ""
                error_message = ""
                for i in data['response']['data']['data']:
                    try:
                        if str(i['friendly_name']) in monitorlist:
                            PlexUsername = (self.t_request("get_user","user_id="+str(i['user_id'])))['response']['data']['username']
                            if i['duration'] is None:
                                print(PlexUsername + " has not watched anything. Purging...")
                                mention_id = await self.remove_winner(str(PlexUsername))
                                removed_list = removed_list + (mention_id if mention_id != None else "")
                            elif i['last_seen'] is None:
                                print(PlexUsername + " has never been seen. Purging...")
                                mention_id = await self.remove_winner(str(PlexUsername))
                                removed_list = removed_list + (mention_id if mention_id != None else "")
                            elif i['duration']/3600 < WINNER_THRESHOLD:
                                print(PlexUsername + " has NOT met the duration requirements. Purging...")
                                mention_id = await self.remove_winner(str(PlexUsername))
                                removed_list = removed_list + (mention_id if mention_id != None else "")
                            elif time.time()-i['last_seen'] > 1209600:
                                print(PlexUsername + " last seen too long ago. Purging...")
                                mention_id = await self.remove_winner(str(PlexUsername))
                                removed_list = removed_list + (mention_id if mention_id != None else "")
                            else:
                                print(PlexUsername + " has met the requirements, and will not be purged.")
                    except Exception as e:
                        print(e)
                        error_message = error_message = "Error checking " + str(i['friendly_name']) + ". "
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
        try:
            self.delete_from_plex(username)
        except plexapi.exceptions.BadRequest:
            pass
        id = self.find_user_in_db("Discord", username)
        if id != None:
            user = self.bot.get_user(int(id))
            await user.create_dm()
            await user.dm_channel.send("You have been removed from " + str(PLEX_SERVER_NAME) + " due to inactivity.")
            await user.remove_roles(discord.utils.get(self.bot.get_guild(int(SERVER_ID)).roles, name="Winner"), reason="Inactive winner")
            self.remove_user_from_db(id)
            return "<@" + id + ">, "
        else:
            return None
           
    def remove_nonsub(self, memberID):
        if memberID not in exemptsubs:
            self.delete_from_plex(memberID)
    
    @tasks.loop(seconds=SUB_CHECK_TIME*(3600*24))
    async def check_subs(self):
        print("Checking Plex subs...")
        myConnection = mysql.connector.connect(host=dbhostname,port=dbport,user=dbusername,passwd=dbpassword,db=database)
        if myConnection.is_connected():
            cur = myConnection.cursor(buffered=True)
            query = "SELECT * FROM users"
            cur.execute(str(query))
            exemptRoles = []
            allRoles = self.bot.get_guild(int(SERVER_ID)).roles
            for r in allRoles:
                if r.name in subRoles:
                    exemptRoles.append(r)
            for member in self.bot.get_guild(int(SERVER_ID)).members:
                if not any(x in member.roles for x in exemptRoles):
                    self.remove_nonsub(member.id)
            myConnection.close()
        print("Plex subs check complete.")
        
    @tasks.loop(seconds=TRIAL_CHECK_FREQUENCY*60)
    async def check_trials(self):
        print("Checking Plex trials...")
        myConnection = mysql.connector.connect(host=dbhostname,port=dbport,user=dbusername,passwd=dbpassword,db=database)
        if myConnection.is_connected():
            cur = myConnection.cursor(buffered=True)
            query = "SELECT PlexUsername, DiscordID FROM users WHERE ExpirationStamp<=" + str(int(time.time())) + " AND Note = 't'";
            cur.execute(str(query))
            trial_role = discord.utils.get(self.bot.get_guild(int(SERVER_ID)).roles, name=TRIAL_ROLE_NAME)
            for u in cur:
                self.delete_from_plex(u[0])
                self.delete_from_tautulli(u[0])
                user = self.bot.get_guild(int(SERVER_ID)).get_member(u[1])
                await user.create_dm()
                await user.dm_channel.send(TRIAL_END_NOTIFICATION)
                await user.remove_roles(trial_role, reason="Trial has ended.")
                self.remove_user_from_db(u[1])
            cur.close()
            myConnection.close()
        print("Plex trials check complete.")
        
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
        if not REACT_TO_ADD:
            added = False
            await ctx.send('Adding ' + PlexUsername + ' to Plex. Please wait about 60 seconds...')
            try:
                winner_role = discord.utils.get(ctx.message.guild.roles, name=WINNER_ROLE_NAME)
                if winner_role in user.roles:
                    added = await self.add_to_plex(PlexUsername, user.id, 'w')
                else:
                    added = await self.add_to_plex(PlexUsername, user.id, 's')
                if added:
                    role = discord.utils.get(ctx.message.guild.roles, name=afterApprovedRoleName)
                    await user.add_roles(role, reason="Access membership channels")
                    await ctx.send(user.mention + " You've been invited, " + PlexUsername + ". Welcome to " + PLEX_SERVER_NAME + "!")
                else:
                    await ctx.send(user.name + " could not be added to Plex.")
            except plexapi.exceptions.BadRequest:
                await ctx.send(PlexUsername + " is not a valid Plex username.")
        else:
            await ctx.send('This function is disabled. Please react to usernames to add to Plex.')
            
    @pm_add.error
    async def pm_add_error(self, ctx, error):
        print(error)
        await ctx.send("Please mention the Discord user to add to Plex, as well as their Plex username.")
            
    @pm.command(name="remove",alias=["uninvite","delete","rem"])
    @commands.has_role(ADMIN_ROLE_NAME)
    async def pm_remove(self, ctx: commands.Context, user: discord.Member):
        """
        Remove a Discord user from Plex
        """
        if not REACT_TO_ADD:
            print(user.id)
            deleted = self.delete_from_plex(user.id)
            print(deleted)
            if deleted:
                role = discord.utils.get(ctx.message.guild.roles, name=afterApprovedRoleName)
                await user.remove_roles(role, reason="Removed from Plex")
                await ctx.send("You've been removed from " + PLEX_SERVER_NAME + ", " + user.mention + ".")
            else:
                await ctx.send("User could not be removed.")
        else:
            await ctx.send('This function is disabled. Please remove a reaction from usernames to remove from Plex.')
    
    @pm_remove.error
    async def pm_remove_error(self, ctx, error):
        await ctx.send("Please mention the Discord user to remove from Plex.")
        
    @pm.command(name="trial")
    @commands.has_role(ADMIN_ROLE_NAME)
    async def pm_trial(self, ctx: commands.Context, user: discord.Member, PlexUsername: str):
        """
        Start a Plex trial
        """
        await ctx.send('Starting ' + PLEX_SERVER_NAME + ' trial for ' + PlexUsername + '. Please wait about 60 seconds...')
        try:
            await self.add_to_plex(PlexUsername, user.id, 't')
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
        name, note = self.find_user_in_db("Plex", user.id)
        await ctx.send(user.mention + " is Plex user: " + name + (" [Trial]" if note == 't' else " [Subscriber]"))
        
    @pm_find.command(name="discord", aliases=["d"])
    async def pm_find_discord(self, ctx: commands.Context, PlexUsername: str):
        """
        Find Plex user's Discord name
        """
        id = self.find_user_in_db("Discord", PlexUsername)
        await ctx.send(PlexUsername + " is Discord user: " + self.bot.get_user(int(id)).mention)
            
    @pm_find.error
    async def pm_find_error(self, ctx, error):
        await ctx.send("User not found.")
            
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
        n = self.describe_table("users")
        d = self.pull_user_from_db("Plex", PlexUsername)
        for i in range(0,len(n)):
            val=str(d[i])
            if str(n[i][0]) == "DiscordID":
                val=val+" ("+self.bot.get_user(int(d[i])).mention+")"
            if str(n[i][0]) == "Note":
                val=("Trial" if d[i] == 't' else "Subscriber")
            if d[i] != None:
                embed.add_field(name=str(n[i][0]),value=val,inline=False)
        await ctx.send(embed=embed)
        
    @pm_info.command(name="discord", aliases=["d"])
    @commands.has_role(ADMIN_ROLE_NAME)
    async def pm_info_discord(self, ctx, user: discord.Member):
        """
        Get database entry for Discord user
        """
        embed = discord.Embed(title=("Info for " + user.name))
        n = self.describe_table("users")
        d = self.pull_user_from_db("Discord", user.id)
        for i in range(0,len(n)):
            name=str(n[i][0])
            val=str(d[i])
            if str(n[i][0]) == "DiscordID":
                val=val+" ("+self.bot.get_user(int(d[i])).mention+")"
            if str(n[i][0]) == "Note":
                val=("Trial" if d[i] == 't' else "Subscriber")
            if d[i] != None:
                embed.add_field(name=str(n[i][0]),value=val,inline=False)
        await ctx.send(embed=embed)
        
    @pm_info.error
    async def pm_info_error(self, ctx, error):
        await ctx.send("User not found.")
        
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if (REACT_TO_ADD) and (reaction.emoji.name == approvedEmojiName) and (user.id in ADMIN_ID): #Add user to Plex and Tautulli
            plexname = reaction.message.content.strip() #Only include username, nothing else
            await reaction.message.channel.send("Adding " + plexname + ". Please wait about 60 seconds...")
            try:
                winner_role = discord.utils.get(reaction.message.guild.roles, name=WINNER_ROLE_NAME)
                if winner_role in reaction.message.author.roles:
                    await self.add_to_plex(plexname, reaction.message.author.id, 'w')
                else:
                    await self.add_to_plex(plexname, reaction.message.author.id, 's')
                member = reaction.message.author
                role = discord.utils.get(reaction.message.guild.roles, name=afterApprovedRoleName)
                await member.add_roles(role, reason="Access membership channels")
                await reaction.message.channel.send(member.mention + " You've been invited, " + plexname + ". Welcome to " + PLEX_SERVER_NAME + "!")
            except plexapi.exceptions.BadRequest:
                await reaction.message.channel.send(reaction.message.author.mention + ", " + plexname + " is not a valid Plex username.")

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        if (REACT_TO_ADD) and (reaction.emoji.name == approvedEmojiName) and (user.name in ADMIN_USERNAME): #Listen for users removed
            plexname = reaction.message.content.strip() #Only include username, nothing else
            self.delete_from_plex(plexname)
            await reaction.message.channel.send(reaction.message.author.mention + " (" + plexname + "), you have been removed from " + PLEX_SERVER_NAME + ". To appeal this removal, please send a Direct Message to <@" + ADMIN_ID + ">")
            
    @commands.bot.listen()
    async def on_ready():
        self.check_trials.start()
        self.check_subs.start()

    def __init__(self, bot):
        self.bot = bot
        print("Plex Manager ready to go.")
