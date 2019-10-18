"""
Interact with a Plex Media Server, manage users
Copyright (C) 2019 Nathan Harris
"""

import discord
from discord.ext import commands, tasks
import requests
import asyncio
import datetime
import time
from plexapi.server import PlexServer
import plexapi
from plexapi.myplex import MyPlexAccount
#import mysql.connector
import urllib
import json
import re
from discord.ext import commands
import sys, traceback, os

MULTI_PLEX = False

plex = "" # Blank variable, do not edit
if MULTI_PLEX:
    PLEX_SERVER_URLS_LIST = []
    PLEX_SERVER_TOKENS_LIST = []
    PLEX_SERVER_NAMES_LIST = []
else:
    # Plex Server settings
    PLEX_SERVER_NAME = os.environ.get("PLEX_SERVER_NAME")
    PLEX_SERVER_ALT_NAME = ""
    if "PLEX_SERVER_ALT_NAME" in os.environ:
        PLEX_SERVER_ALT_NAME = os.environ.get("PLEX_SERVER_ALT_NAME")
    plex = PlexServer(os.environ.get('PLEX_URL'), os.environ.get('PLEX_TOKEN'))

# Ombi settings
USE_OMBI = True

# Tautulli settings
USE_TAUTULLI = True
MULTI_TAUTULLI = False

if MULTI_TAUTULLI:
    TAUTULLI_URL_LIST = []
    TAUTULLI_KEY_LIST = []

# Discord (Admin) settings
SERVER_ID = os.environ.get('DISCORD_SERVER_ID')
ADMIN_ID = os.environ.get('ADMIN_ID')
ADMIN_ROLE_NAME = "Admin"
AFTER_APPROVED_ROLE_NAME = "Invited"
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

# Winner settings
WINNER_ROLE_NAME = "Winner"
WINNER_THRESHOLD = 2 # hours
AUTO_WINNERS = False
# True:
# Messages from the indicated GIVEAWAY_BOT_ID user will be scanned for mentioned Discord users (winners).
# The winners will be auto-assigned the TEMP_WINNER_ROLE_NAME. That role gives them access to a specificed WINNER_CHANNEL channel
# Users then post their Plex username (ONLY their Plex username) in the channel, which is processed by the bot.
# The bot invites the Plex username, and associates the Discord user author of the message with the Plex username in the database.
# The user is then have the TEMP_WINNER_ROLE_NAME role removed (which removes them from the WINNER_CHANNEL channel), and assigned the final WINNER_ROLE_NAME role.
if AUTO_WINNERS:
    TEMP_WINNER_ROLE_NAME = "Uninvited Winner"
    WINNER_CHANNEL = 0 # Channel ID
    GIVEAWAY_BOT_ID = 0

# Logging settings
FRIENDLY_LOGGING = False
#FRIENDLY_LOG_CHANNEL_ID = ###########
VERBOSE_LOGGING = False
#VERBOSE_LOG_CHANNEL_ID = ###############



### DO NOT EDIT
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
    
    def countServerSubs(self, serverNumber):
        tempPlex = plex
        tempServerName = ""
        if serverNumber >= 0:
            tempPlex = PlexServer(PLEX_SERVER_URLS_LIST[serverNumber],PLEX_SERVER_TOKENS_LIST[serverNumber])
            tempServerName = PLEX_SERVER_NAMES_LIST[serverNumber]
        else:
            tempServerName = PLEX_SERVER_NAME
        count = 0
        for u in tempPlex.myPlexAccount().users():
            for s in u.servers:
                if s.name == tempServerName:
                        count+=1
        return count
        
    def t_request(self, cmd, params, serverNumber=None):
        if serverNumber and serverNumber < len(TAUTULLI_URL_LIST):
            return json.loads(requests.get(TAUTULLI_URL_LIST[serverNumber-1] + "/api/v2?apikey=" + TAUTULLI_KEY_LIST[serverNumber-1] + "&cmd=" + str(cmd) + (("&" + str(params)) if params != None else "")).text)
        else:
            return json.loads(requests.get(os.environ.get('TAUTULLI_URL') + "/api/v2?apikey=" + os.environ.get('TAUTULLI_KEY') + "&cmd=" + str(cmd) + (("&" + str(params)) if params != None else "")).text)
    
    def add_to_tautulli(self, plexname, serverNumber=None):
        if USE_TAUTULLI == False:
            pass
        else:
            response = self.t_request("refresh_users_list",None,serverNumber)
        
    def delete_from_tautulli(self, plexname, serverNumber=None):
        if not USE_TAUTULLI:
            pass
        else:
            response = self.t_request("delete_user","user_id=" + str(plexname),serverNumber)
        
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

    async def add_to_plex(self, plexname, note, serverNumber = None):
        tempPlex = plex;
        if serverNumber != None:
            tempPlex = PlexServer(PLEX_SERVER_URLS_LIST[serverNumber],PLEX_SERVER_TOKENS_LIST[serverNumber])
        try:
            tempPlex.myPlexAccount().inviteFriend(user=plexname,server=plex,sections=None, allowSync=False, allowCameraUpload=False, allowChannels=False, filterMovies=None, filterTelevision=None, filterMusic=None)
            await asyncio.sleep(60)
            self.add_to_tautulli(plexname, serverNumber)
            if note != 't': # Trial members do not have access to Ombi
                self.add_to_ombi(plexname)
            return True
        except Exception as e:
            print(e)
            return False
        
    def delete_from_plex(self, plexname, serverNumber = None):
        tempPlex = plex;
        if serverNumber != None:
            tempPlex = PlexServer(PLEX_SERVER_URLS_LIST[serverNumber],PLEX_SERVER_TOKENS_LIST[serverNumber])
        try:
            tempPlex.myPlexAccount().removeFriend(user=plexname)
            self.delete_from_ombi(plexname) # Error if trying to remove trial user that doesn't exist in Ombi?
            self.delete_from_tautulli(plexname, serverNumber)
            return True
        except plexapi.exceptions.NotFound:
            #print("Not found")
            return False
        
    @commands.group(name="pm",aliases=["PM","PlexMan","plexman"],pass_context=True)
    async def pm(self, ctx: commands.Context):
        """
        Plex admin commands
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")
            
    @pm.command(name="access", pass_context=True)
    ### Anyone can use this command
    async def pm_access(self, ctx: commands.Context, PlexUsername: str):
        """
        Check if you or another user has access to the Plex server
        """
        hasAccess = False
        name = PlexUsername
        serverNumber = 0
        if name != None:
            if MULTI_PLEX:
                for i in range(0,len(PLEX_SERVER_URLS_LIST)):
                    tempPlex = PlexServer(PLEX_SERVER_URLS_LIST[i],PLEX_SERVER_TOKENS_LIST[i])
                    for u in tempPlex.myPlexAccount().users():
                        if u.username == name:
                            for s in u.servers:
                                if s.name == PLEX_SERVER_NAMES_LIST[i]:
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
                await ctx.send(("You have" if PlexUsername is None else name + " has") + " access to " + (PLEX_SERVER_NAMES_LIST[i] if MULTI_PLEX else PLEX_SERVER_NAME))
            else:
                await ctx.send(("You do not have" if PlexUsername is None else name + " does not have") + " access to " + ("any of the Plex servers" if MULTI_PLEX else PLEX_SERVER_NAME))
        else:
            await ctx.send("User not found.")
            
    @pm_access.error
    async def pm_access_error(self, ctx, error):
        await ctx.send("Sorry, something went wrong.")
        
    @pm.command(name="status", aliases=['ping','up','online'], pass_context=True)
    async def pm_status(self, ctx: commands.Context):
        """
        Check if the Plex server(s) is/are online
        """
        status = ""
        if MULTI_PLEX:
            for i in range(0,len(PLEX_SERVER_URLS_LIST)):
                r = requests.get(PLEX_SERVER_URLS_LIST[i] + "/identity", timeout=10)
                if r.status_code != 200:
                    status = status + PLEX_SERVER_NAME + " is having connection issues right now.\n"
                else:
                   status = status + PLEX_SERVER_NAME + " is up and running.\n"
        else:
            r = requests.get(os.environ.get('PLEX_URL') + "/identity", timeout=10)
            if r.status_code != 200:
                status = PLEX_SERVER_NAME + " is having connection issues right now."
            else:
                status = PLEX_SERVER_NAME + " is up and running."
        await ctx.send(status)
            
    @pm_status.error
    async def pm_status_error(self, ctx, error):
        await ctx.send("Sorry, I couldn't test the " + ("connections." if MULTI_PLEX else "connection."))
        
    @pm.command(name="count")
    @commands.has_role(ADMIN_ROLE_NAME)
    async def pm_count(self, ctx: commands.Context, serverNumber: int = None):
        """
        Check Plex share count
        Include optional serverNumber to check a specific Plex server (if using multiple servers)
        """
        if MULTI_PLEX:
            if serverNumber == None:
                totals = ""
                for i in range(0,len(PLEX_SERVER_URLS_LIST)):
                    totals = totals + PLEX_SERVER_NAMES_LIST[i] + " has " + str(self.countServerSubs(i)) + " users\n"
                await ctx.send(totals)
            else:
                if serverNumber <= len(PLEX_SERVER_URLS_LIST):
                    await ctx.send(PLEX_SERVER_NAMES_LIST[serverNumber-1] + " has " + str(self.countServerSubs(serverNumber-1)) + " users")
                else:
                    await ctx.send("That server number does not exist.")
        else:
            await ctx.send(PLEX_SERVER_NAME + " has " + str(self.countServerSubs(-1)) + " users")
        
    @pm_count.error
    async def pm_count_error(self, ctx, error):
        print(error)
        await ctx.send("Something went wrong. Please try again later.")
        
    @pm.command(name="add",alias=["invite","new"])
    @commands.has_role(ADMIN_ROLE_NAME)
    async def pm_add(self, ctx: commands.Context, user: discord.Member, PlexUsername: str, serverNumber: int = None):
        """
        Add a Discord user to Plex
        Mention the Discord user and their Plex username
        Include optional serverNumber to add to a specific server (if using multiple Plex servers)
        """
        if not REACT_TO_ADD:
            added = False
            if MULTI_PLEX:
                if serverNumber == None: # No specific number indicated. Defaults adding to the least-fill server
                    smallestCount = 100
                    for i in range(0,len(PLEX_SERVER_URLS_LIST)):
                        if self.countServerSubs(i) < smallestCount:
                            serverNumber = i
                elif serverNumber > len(PLEX_SERVER_URLS_LIST) - 1:
                    await ctx.send("That server number does not exist.")
                else:
                    serverNumber = serverNumber - 1
                await ctx.send('Adding ' + PlexUsername + ' to ' + PLEX_SERVER_NAMES_LIST[serverNumber] + '. Please wait about 60 seconds...')
                try:
                    added = await self.add_to_plex(PlexUsername, user.id, 's', serverNumber)
                    if added:
                        role = discord.utils.get(ctx.message.guild.roles, name=AFTER_APPROVED_ROLE_NAME)
                        await user.add_roles(role, reason="Access membership channels")
                        await ctx.send(user.mention + " You've been invited, " + PlexUsername + ". Welcome to " + PLEX_SERVER_NAMES_LIST[serverNumber] + "!")
                    else:
                        await ctx.send(user.name + " could not be added to that server.")
                except plexapi.exceptions.BadRequest:
                    await ctx.send(PlexUsername + " is not a valid Plex username.")   
            else:
                await ctx.send('Adding ' + PlexUsername + ' to ' + PLEX_SERVER_NAME + '. Please wait about 60 seconds...')
                try:
                    added = await self.add_to_plex(PlexUsername, user.id, 's', serverNumber)
                    if added:
                        role = discord.utils.get(ctx.message.guild.roles, name=AFTER_APPROVED_ROLE_NAME)
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
    async def pm_remove(self, ctx: commands.Context, user: discord.Member, PlexUsername: str, serverNumber: int = None):
        """
        Remove a Discord user from Plex
        Mention the Discord user and their Plex username
        Need to include which server to remove the user from
        """
        if not REACT_TO_ADD:
            if MULTI_PLEX:
                if serverNumber > len(PLEX_SERVER_URLS_LIST) - 1:
                    await ctx.send("That server number does not exist.")
                else:
                    serverNumber = serverNumber - 1
                deleted = self.delete_from_plex(PlexUsername, serverNumber)
                if deleted:
                    role = discord.utils.get(ctx.message.guild.roles, name=AFTER_APPROVED_ROLE_NAME)
                    await user.remove_roles(role, reason="Removed from Plex")
                    await ctx.send("You've been removed from " + PLEX_SERVER_NAME + ", " + user.mention + ".")
                else:
                    await ctx.send("User could not be removed.")
            else:
                deleted = self.delete_from_plex(PlexUsername)
                if deleted:
                    role = discord.utils.get(ctx.message.guild.roles, name=AFTER_APPROVED_ROLE_NAME)
                    await user.remove_roles(role, reason="Removed from Plex")
                    await ctx.send("You've been removed from " + PLEX_SERVER_NAME + ", " + user.mention + ".")
                else:
                    await ctx.send("User could not be removed.")
        else:
            await ctx.send('This function is disabled. Please remove a reaction from usernames to remove from Plex.')
        
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if (REACT_TO_ADD) and (reaction.emoji.name == approvedEmojiName) and (user.id in ADMIN_ID): #Add user to Plex and Tautulli
            plexname = reaction.message.content.strip() #Only include username, nothing else
            await reaction.message.channel.send("Adding " + plexname + ". Please wait about 60 seconds...")
            try:
                await self.add_to_plex(plexname, 's')
                member = reaction.message.author
                role = discord.utils.get(reaction.message.guild.roles, name=AFTER_APPROVED_ROLE_NAME)
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
            
    @commands.Cog.listener()
    async def on_message(self, message):
        if AUTO_WINNERS:
            if message.author.id == GIVEAWAY_BOT_ID and "congratulations" in message.content.lower() and message.mentions:
                tempWinner = discord.utils.get(message.guild.roles, name=TEMP_WINNER_ROLE_NAME)
                for u in message.mentions:
                    await u.add_roles(tempWinner, reason="Winner - access winner invite channel")
            if message.channel.id == WINNER_CHANNEL and discord.utils.get(message.guild.roles, name=TEMP_WINNER_ROLE_NAME) in message.author.roles:
                plexname = message.content.strip() #Only include username, nothing else
                await message.channel.send("Adding " + plexname + ". Please wait about 60 seconds...\nBe aware, you will be removed from this channel once you are added successfully.")
                try:
                    serverNumer = -1
                    if MULTI_PLEX:
                        smallestCount = 100
                        for i in range(0,len(PLEX_SERVER_URLS_LIST)):
                            if self.countServerSubs(i) < smallestCount:
                                serverNumber = i
                    await self.add_to_plex(plexname, 'w', serverNumber)
                    await message.channel.send(message.author.mention + " You've been invited, " + plexname + ". Welcome to " + (PLEX_SERVER_NAMES_LIST[serverNumber] if MULTI_PLEX else PLEX_SERVER_NAME) + "!")
                    await message.author.remove_roles(discord.utils.get(message.guild.roles, name=TEMP_WINNER_ROLE_NAME), reason="Winner was processed successfully.")
                except plexapi.exceptions.BadRequest:
                    await message.channel.send(message.author.mention + ", " + plexname + " is not a valid Plex username.")

    def __init__(self, bot):
        self.bot = bot
        print("Plex Manager ready to go.")
