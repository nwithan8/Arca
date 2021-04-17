"""
Interact with a Booksonic audiobook & podcast server via its API
Copyright (C) 2020 Nathan Harris
"""
import discord
from discord.ext import commands
import requests
import xml.etree.ElementTree as ET
import random
import hashlib
import media_server.booksonic.settings as settings
from helper.decorators import has_admin_role

BOOKSONIC_URL = settings.BOOKSONIC_URL
BOOKSONIC_USER = settings.BOOKSONIC_USER
BOOKSONIC_PASS = settings.BOOKSONIC_PASS
BOOKSONIC_SERVER_NAME = settings.BOOKSONIC_SERVER_NAME

# EDIT
DEFAULT_EMAIL = settings.DEFAULT_EMAIL
USE_DEFAULT_PASSWORD = settings.USE_DEFAULT_PASSWORD  # If FALSE, random password generated each time
if USE_DEFAULT_PASSWORD:
    DEFAULT_PASSWORD = settings.DEFAULT_PASSWORD

ADMIN_ROLE_NAME = settings.ADMIN_ROLE_NAME


def password(length):
    ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return ''.join(random.choice(ALPHABET) for _ in range(length))


def makeToken():
    salt = password(10)
    token = hashlib.md5((BOOKSONIC_PASS + salt).encode()).hexdigest()
    return salt, token


def request(cmd, params):
    salt, token = makeToken()
    response = requests.get(
        BOOKSONIC_URL + "/booksonic/rest/" + cmd + ".view?u=" + BOOKSONIC_USER + "&t=" + token + "&s=" + salt + "&v=1.14&c=booksonic" + (
            ("&" + str(params)) if params is not None else ""))
    return ET.fromstring(response.content).get('status')


class Booksonic(commands.Cog):

    @commands.group(aliases=["book", "bs", "books", "Booksonic"], pass_context=True)
    async def booksonic(self, ctx: commands.Context):
        """
        Booksonic server commands
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")

    @booksonic.command(name="add", aliases=["new"], pass_context=True)

    async def booksonic_add(self, ctx: commands.Context, user: discord.Member, booksonicUsername: str):
        """
        Add a Discord user to Booksonic
        """
        p = password(10)
        s = request('createUser', 'username=' + booksonicUsername + "&password=" + (
            DEFAULT_PASSWORD if USE_DEFAULT_PASSWORD else p) + "&email=" + DEFAULT_EMAIL + "&jukeboxRole=true&downloadRole=true&commentRole=true")
        if s == 'ok':
            await user.create_dm()
            await user.dm_channel.send("You have been added to " + str(BOOKSONIC_SERVER_NAME) + "!\n" +
                                       "Hostname: " + str(BOOKSONIC_URL) + "\n" +
                                       "Username: " + str(booksonicUsername) + "\n" +
                                       "Password: " + ((str(
                DEFAULT_PASSWORD) + "\nPlease change this password when you first log in.") if USE_DEFAULT_PASSWORD else str(
                p)) + ".\n" +
                                       "Enjoy!")
            await ctx.send(
                "You've been added, " + user.mention + "! Please check your direct messages for login information.")
        else:
            await ctx.send("User could not be added.")

    @booksonic_add.error
    async def booksonic_add_error(self, ctx, error):
        print(error)
        await ctx.send("Something went wrong. Maybe try adding manually?")

    def __init__(self, bot):
        self.bot = bot
        print("Booksonic, ready to go!")

    @booksonic.command(name="ping", aliases=["test"], pass_context=True)
    async def booksonic_ping(self, ctx: commands.Context):
        """
        Ping the Booksonic server
        """
        s = request('ping', None)
        if s == 'ok':
            await ctx.send(BOOKSONIC_SERVER_NAME + " is up and running.")
        else:
            await ctx.send(BOOKSONIC_SERVER_NAME + " is unavailable.")

    @booksonic_add.error
    async def booksonic_add_error(self, ctx, error):
        print(error)
        await ctx.send("...pong?")

    def __init__(self, bot):
        self.bot = bot
        print("Booksonic, ready to go!")


def setup(bot):
    bot.add_cog(Booksonic(bot))
