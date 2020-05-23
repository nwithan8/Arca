"""
Interact with a Jellyfin Media Server, manage users
Copyright (C) 2019 Nathan Harris
"""

import discord
from discord.ext import commands, tasks
import json
import random
import string
import csv
from datetime import datetime
from collections import defaultdict
import datetime
from decimal import *
import asyncio
from media_server.jellyfin import settings as settings
from media_server.jellyfin import jellyfin_api as jf
from media_server.jellyfin import jellyfin_stats as js
from media_server.jellyfin import jellyfin_recs as jr
from helper.db_commands import DB
from helper.pastebin import hastebin, privatebin
import helper.discord_helper as discord_helper


class Jellyfin(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        jf.authenticate()
        print("Jellyfin ready to go.")

    @commands.group(name="jf", aliases=["jellyfin", "JF"], pass_context=True)
    async def jellyfin(self, ctx: commands.Context):
        """
        jellyfin Media Server commands
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")

    @jellyfin.group(name="rec", aliases=["sug", "recommend", "suggest"], pass_context=True)
    async def jellyfin_rec(self, ctx: commands.Context, mediaType: str):
        """
        Movie, show or artist recommendation from jellyfin

        Say 'movie', 'show' or 'artist'
        Use 'jellyfinrec <mediaType> new <jellyfinUsername>' for an unwatched recommendation.
        """
        if ctx.invoked_subcommand is None:
            mediaType = mediaType.lower()
            if mediaType.lower() not in jr.accepted_types:
                acceptedTypes = "', '".join(jr.accepted_types)
                await ctx.send("Please try again, indicating '{}'".format(acceptedTypes))
            else:
                holdMessage = await ctx.send(
                    "Looking for a{} {}...".format("n" if (mediaType[0] in ['a', 'e', 'i', 'o', 'u']) else "",
                                                   mediaType))
                async with ctx.typing():
                    response, embed, mediaItem = jr.make_recommendation(mediaType=mediaType, unwatched=False)
                await holdMessage.delete()
                if embed is not None:
                    recMessage = await ctx.send(response, embed=embed)
                else:
                    await ctx.send(response)
                if mediaItem and mediaItem.type not in ['artist', 'album', 'track']:
                    await recMessage.add_reaction('🎞️')
                    try:
                        def check(trailerReact, trailerReactUser):
                            return trailerReact.emoji == '🎞️' and trailerReactUser.id != self.bot.user.id

                        showTrailer, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                        if showTrailer:
                            await ctx.send(jr.get_trailer_URL(mediaItem=mediaItem))
                    except asyncio.TimeoutError:
                        await recMessage.clear_reactions()

    @jellyfin_rec.error
    async def jellyfin_rec_error(self, ctx, error):
        print(error)
        await ctx.send("Sorry, something went wrong while looking for a recommendation.")

    @jellyfin_rec.command(name="new", aliases=["unseen", "unwatched"])
    async def jellyfin_rec_new(self, ctx: commands.Context, jellyfinUsername: str):
        """
        Get a new movie, show or artist recommendation
        Include your jellyfin username
        """
        mediaType = None
        for group in jr.accepted_types:
            if group in ctx.message.content.lower():
                mediaType = group
                break
        if not mediaType:
            acceptedTypes = "', '".join(jr.accepted_types)
            await ctx.send("Please try again, indicating '{}'".format(acceptedTypes))
        else:
            holdMessage = await ctx.send("Looking for a new {}...".format(mediaType))
            async with ctx.typing():
                response, embed, mediaItem = jr.make_recommendation(mediaType=mediaType, unwatched=True,
                                                                    username=jellyfinUsername)
            await holdMessage.delete()
            if embed is not None:
                recMessage = await ctx.send(response, embed=embed)
            else:
                await ctx.send(response)
            if mediaItem and mediaItem.type not in ['artist', 'album', 'track']:
                await recMessage.add_reaction('🎞️')
                try:
                    def check(trailerReact, trailerReactUser):
                        return trailerReact.emoji == '🎞️' and trailerReactUser.id != self.bot.user.id

                    showTrailer, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                    if showTrailer:
                        await ctx.send(jr.get_trailer_URL(mediaItem=mediaItem))
                except asyncio.TimeoutError:
                    await recMessage.clear_reactions()

    @jellyfin_rec_new.error
    async def jellyfin_rec_new_error(self, ctx, error):
        print(error)
        await ctx.send("Sorry, something went wrong while looking for a new recommendation.")


def setup(bot):
    bot.add_cog(Jellyfin(bot))
