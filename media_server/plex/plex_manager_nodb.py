"""
Interact with a Plex Media Server, manage users
Copyright (C) 2019 Nathan Harris
"""

import discord
import requests
import asyncio
from plexapi.server import PlexServer
import plexapi
from discord.ext import commands
from media_server.plex import settings as settings
from media_server.plex import plex_api as px

plex = px.plex

REACT_TO_ADD = False  # Ignore, depreciated


async def add_to_plex(plexname, note, serverNumber=None):
    tempPlex = plex
    if serverNumber:
        tempPlex = PlexServer(settings.PLEX_SERVER_URL[serverNumber], settings.PLEX_SERVER_TOKEN[serverNumber])
    try:
        tempPlex.myPlexAccount().inviteFriend(user=plexname, server=tempPlex, sections=None, allowSync=False,
                                              allowCameraUpload=False, allowChannels=False, filterMovies=None,
                                              filterTelevision=None, filterMusic=None)
        await asyncio.sleep(60)
        px.add_to_tautulli(plexname, serverNumber)
        if note != 't':  # Trial members do not have access to Ombi
            px.add_to_ombi(plexname)
        return True
    except Exception as e:
        print(e)
        return False


def delete_from_plex(plexname, serverNumber=None):
    tempPlex = plex;
    if serverNumber:
        tempPlex = PlexServer(settings.PLEX_SERVER_URL[serverNumber], settings.PLEX_SERVER_TOKEN[serverNumber])
    try:
        tempPlex.myPlexAccount().removeFriend(user=plexname)
        px.delete_from_ombi(plexname)  # Error if trying to remove trial user that doesn't exist in Ombi?
        px.delete_from_tautulli(plexname, serverNumber)
        return True
    except plexapi.exceptions.NotFound:
        print("Couldn't delete user {}".format(plexname))
        return False


class PlexManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="pm", aliases=["PM", "PlexMan", "plexman"], pass_context=True)
    async def pm(self, ctx: commands.Context):
        """
        Plex admin commands
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")

    @pm.command(name="access", pass_context=True)
    # Anyone can use this command
    async def pm_access(self, ctx: commands.Context, PlexUsername: str):
        """
        Check if you or another user has access to the Plex server
        """
        hasAccess = False
        name = PlexUsername
        serverNumber = 0
        if name:
            if settings.MULTI_PLEX:
                for i in range(0, len(settings.PLEX_SERVER_URL)):
                    tempPlex = PlexServer(settings.PLEX_SERVER_URL[i], settings.PLEX_SERVER_TOKEN[i])
                    for u in tempPlex.myPlexAccount().users():
                        if u.username == name:
                            for s in u.servers:
                                if s.name == settings.PLEX_SERVER_NAME[i] or s.name == settings.PLEX_SERVER_ALT_NAME[i]:
                                    hasAccess = True
                                    serverNumber = i
                                    break
                            break
                    break
            else:
                for u in plex.myPlexAccount().users():
                    if u.username == name:
                        for s in u.servers:
                            if s.name == settings.PLEX_SERVER_NAME or s.name == settings.PLEX_SERVER_ALT_NAME:
                                hasAccess = True
                                break
                        break
            if hasAccess:
                await ctx.send(("You have" if PlexUsername is None else name + " has") + " access to " + (
                    settings.PLEX_SERVER_NAME[serverNumber] if settings.MULTI_PLEX else settings.PLEX_SERVER_NAME))
            else:
                await ctx.send(
                    ("You do not have" if PlexUsername is None else name + " does not have") + " access to " + (
                        "any of the Plex servers" if settings.MULTI_PLEX else settings.PLEX_SERVER_NAME))
        else:
            await ctx.send("User not found.")

    @pm_access.error
    async def pm_access_error(self, ctx, error):
        print(error)
        await ctx.send("Sorry, something went wrong.")

    @pm.command(name="status", aliases=['ping', 'up', 'online'], pass_context=True)
    async def pm_status(self, ctx: commands.Context):
        """
        Check if the Plex server(s) is/are online
        """
        status = ""
        if settings.MULTI_PLEX:
            for i in range(0, len(settings.PLEX_SERVER_URL)):
                r = requests.get(settings.PLEX_SERVER_URL[i] + "/identity", timeout=10)
                if r.status_code != 200:
                    status = status + settings.PLEX_SERVER_NAME[i] + " is having connection issues right now.\n"
                else:
                    status = status + settings.PLEX_SERVER_NAME[i] + " is up and running.\n"
        else:
            r = requests.get(settings.PLEX_SERVER_URL + "/identity", timeout=10)
            if r.status_code != 200:
                status = settings.PLEX_SERVER_NAME + " is having connection issues right now."
            else:
                status = settings.PLEX_SERVER_NAME + " is up and running."
        await ctx.send(status)

    @pm_status.error
    async def pm_status_error(self, ctx, error):
        print(error)
        await ctx.send("Sorry, I couldn't test the " + ("connections." if settings.MULTI_PLEX else "connection."))

    @pm.command(name="count")
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def pm_count(self, ctx: commands.Context, serverNumber: int = None):
        """
        Check Plex share count
        Include optional serverNumber to check a specific Plex server (if using multiple servers)
        """
        if settings.MULTI_PLEX:
            if not serverNumber:
                totals = ""
                for i in range(0, len(settings.PLEX_SERVER_URL)):
                    totals = totals + settings.PLEX_SERVER_NAME[i] + " has " + str(px.countServerSubs(i)) + " users\n"
                await ctx.send(totals)
            else:
                if serverNumber <= len(settings.PLEX_SERVER_URL):
                    await ctx.send(settings.PLEX_SERVER_NAME[serverNumber - 1] + " has " + str(
                        px.countServerSubs(serverNumber - 1)) + " users")
                else:
                    await ctx.send("That server number does not exist.")
        else:
            await ctx.send(settings.PLEX_SERVER_NAME + " has " + str(px.countServerSubs(-1)) + " users")

    @pm_count.error
    async def pm_count_error(self, ctx, error):
        print(error)
        await ctx.send("Something went wrong. Please try again later.")

    @pm.command(name="add", alias=["invite", "new"], pass_context=True)
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def pm_add(self, ctx: commands.Context, user: discord.Member, PlexUsername: str, serverNumber: int = None):
        """
        Add a Discord user to Plex
        Mention the Discord user and their Plex username
        Include optional serverNumber to add to a specific server (if using multiple Plex servers)
        """
        if not REACT_TO_ADD:
            if settings.MULTI_PLEX:
                if not serverNumber:  # No specific number indicated. Defaults adding to the least-fill server
                    serverNumber = px.getSmallestServer()
                elif serverNumber > len(settings.PLEX_SERVER_URL):
                    await ctx.send("That server number does not exist.")
                else:
                    serverNumber = serverNumber - 1  # user's "server 5" is really server 4 in the index
                await ctx.send('Adding ' + PlexUsername + ' to ' + settings.PLEX_SERVER_NAME[
                    serverNumber] + '. Please wait about 60 seconds...')
                try:
                    added = await add_to_plex(PlexUsername, 's', serverNumber)
                    if added:
                        role = discord.utils.get(ctx.message.guild.roles, name=settings.AFTER_APPROVED_ROLE_NAME)
                        await user.add_roles(role, reason="Access membership channels")
                        await ctx.send(user.mention + " You've been invited, " + PlexUsername + ". Welcome to " +
                                       settings.PLEX_SERVER_NAME[serverNumber] + "!")
                    else:
                        await ctx.send(user.name + " could not be added to that server.")
                except plexapi.exceptions.BadRequest:
                    await ctx.send(PlexUsername + " is not a valid Plex username.")
            else:
                await ctx.send(
                    'Adding ' + PlexUsername + ' to ' + settings.PLEX_SERVER_NAME + '. Please wait about 60 seconds...')
                try:
                    added = await add_to_plex(PlexUsername, 's', serverNumber)
                    if added:
                        role = discord.utils.get(ctx.message.guild.roles, name=settings.AFTER_APPROVED_ROLE_NAME)
                        await user.add_roles(role, reason="Access membership channels")
                        await ctx.send(
                            user.mention + " You've been invited, " + PlexUsername + ". Welcome to " + settings.PLEX_SERVER_NAME + "!")
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

    @pm.command(name="remove", alias=["uninvite", "delete", "rem"])
    @commands.has_role(settings.DISCORD_ADMIN_ROLE_NAME)
    async def pm_remove(self, ctx: commands.Context, user: discord.Member, PlexUsername: str, serverNumber: int = None):
        """
        Remove a Discord user from Plex
        Mention the Discord user and their Plex username
        Need to include which server to remove the user from
        """
        if not REACT_TO_ADD:
            if settings.MULTI_PLEX:
                if serverNumber > len(settings.PLEX_SERVER_URL) - 1:
                    await ctx.send("That server number does not exist.")
                else:
                    serverNumber = serverNumber - 1
                deleted = delete_from_plex(PlexUsername, serverNumber)
                if deleted:
                    role = discord.utils.get(ctx.message.guild.roles, name=settings.AFTER_APPROVED_ROLE_NAME)
                    await user.remove_roles(role, reason="Removed from Plex")
                    await ctx.send("You've been removed from " + settings.PLEX_SERVER_NAME + ", " + user.mention + ".")
                else:
                    await ctx.send("User could not be removed.")
            else:
                deleted = delete_from_plex(PlexUsername)
                if deleted:
                    role = discord.utils.get(ctx.message.guild.roles, name=settings.AFTER_APPROVED_ROLE_NAME)
                    await user.remove_roles(role, reason="Removed from Plex")
                    await ctx.send("You've been removed from " + settings.PLEX_SERVER_NAME + ", " + user.mention + ".")
                else:
                    await ctx.send("User could not be removed.")
        else:
            await ctx.send('This function is disabled. Please remove a reaction from usernames to remove from Plex.')

    @pm_remove.error
    async def pm_remove_error(self, ctx, error):
        await ctx.send("Please mention the Discord user to remove from Plex.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if settings.AUTO_WINNERS:
            if message.author.id == settings.GIVEAWAY_BOT_ID and "congratulations" in message.content.lower() and message.mentions:
                tempWinner = discord.utils.get(message.guild.roles, name=settings.TEMP_WINNER_ROLE_NAME)
                for u in message.mentions:
                    await u.add_roles(tempWinner, reason="Winner - access winner invite channel")
            if message.channel.id == settings.WINNER_CHANNEL and discord.utils.get(message.guild.roles,
                                                                                   name=settings.TEMP_WINNER_ROLE_NAME) in message.author.roles:
                plexname = message.content.strip()  # Only include username, nothing else
                await message.channel.send(
                    "Adding " + plexname + ". Please wait about 60 seconds...\nBe aware, you will be removed from "
                                           "this channel once you are added successfully.")
                try:
                    serverNumber = None
                    if settings.MULTI_PLEX:
                        serverNumber = px.getSmallestServer()
                    await add_to_plex(plexname, 'w', serverNumber)
                    await message.channel.send(
                        message.author.mention + " You've been invited, " + plexname + ". Welcome to " + (
                            settings.PLEX_SERVER_NAME[
                                serverNumber] if settings.MULTI_PLEX else settings.PLEX_SERVER_NAME) + "!")
                    await message.author.remove_roles(
                        discord.utils.get(message.guild.roles, name=settings.TEMP_WINNER_ROLE_NAME),
                        reason="Winner was processed successfully.")
                except plexapi.exceptions.BadRequest:
                    await message.channel.send(
                        message.author.mention + ", " + plexname + " is not a valid Plex username.")

    def __init__(self, bot):
        self.bot = bot
        print("Plex Manager ready to go.")


def setup(bot):
    bot.add_cog(PlexManager(bot))
