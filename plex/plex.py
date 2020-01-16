"""
Parse Plex Media Server statistics via Tautulli's API
Copyright (C) 2019 Nathan Harris
"""

import discord
from discord.ext import commands, tasks
from discord.utils import get
from plexapi.server import PlexServer
from collections import defaultdict
import random
from imdbpie import Imdb
from imdbpie import ImdbFacade
import re
import json
import requests
import xml.etree.ElementTree as ET
# from progress.bar import Bar
import os
import datetime
from decimal import *
import math
import asyncio
from plex.encryption import Encryption
from os.path import exists
import xml.etree.ElementTree as ET
from plex.db_commands import DB

# Discord-to-Plex database (SQLite3)
SQLITE_FILE = 'plex/PlexDiscord.db'  # File path + name + extension (i.e.
# "/root/nwithan8-cogs/plex_manager/PlexDiscord.db"
db = DB(SQLITE_FILE, None, None)

PLEX_URL = os.environ.get('PLEX_URL')
PLEX_TOKEN = os.environ.get('PLEX_TOKEN')
PLEX_SERVER_ID = os.environ.get('PLEX_SERVER_ID')  # after "/server/" in browser UI URL
SERVER_NICKNAME = os.environ.get('PLEX_SERVER_NAME')

ADMIN_ROLE_NAME = "Admin"

# http://[PMS_IP_Address]:32400/library/sections?X-Plex-Token=YourTokenGoesHere
# Use the above link to find the number for each library: composite="/library/sections/NUMBER/composite/..."
MOVIE_LIBRARY = 1  # Might be different for your Plex library
TV_LIBRARY = 2  # Might be different for your Plex library
MOVIE_LIBRARY_NAME = 'Movies'
TV_SHOW_LIBRARY_NAME = 'TV Shows'

TAUTULLI_BASE_URL = os.environ.get('TAUTULLI_URL')
TAUTULLI_API_KEY = os.environ.get('TAUTULLI_KEY')

plex = PlexServer(PLEX_URL, PLEX_TOKEN)

credentials_folder = 'plex/credentials'
crypt = Encryption('{}/credskey.txt'.format(credentials_folder))

imdbf = ImdbFacade()
imdb = Imdb()

owner_players = []
# Numbers 1-9
emoji_numbers = [u"1\u20e3", u"2\u20e3", u"3\u20e3", u"4\u20e3", u"5\u20e3", u"6\u20e3", u"7\u20e3", u"8\u20e3",
                 u"9\u20e3"]
session_ids = []

shows = defaultdict(list)
movies = defaultdict(list)

terminate_message = "Please direct message @Nate in the Discord server."

subscriber_watchlist_title = "{}'s Watchlist"
subscriber_playlist_title = "{}'s Playlist"

def request(cmd, params):
    return json.loads(requests.get(
        TAUTULLI_BASE_URL + "/api/v2?apikey=" + TAUTULLI_API_KEY + "&" + str(params) + "&cmd=" + str(
            cmd)).text if params is not None else requests.get(
        TAUTULLI_BASE_URL + "/api/v2?apikey=" + TAUTULLI_API_KEY + "&cmd=" + str(cmd)).text)


def filesize(size):
    pf = ['Byte', 'Kilobyte', 'Megabyte', 'Gigabyte', 'Terabyte', 'Petabyte', 'Exabyte', 'Zettabyte', 'Yottabyte']
    i = 0
    while size > 1024:
        i += 1
        size /= 1024
    return "{:.2f}".format(size) + " " + pf[i] + ("s" if size != 1 else "")


def getposter(att, title):
    try:
        att.set_image(url=str(imdbf.get_title(imdb.search_for_title(title)[0]['imdb_id']).image.url))
        return att
    except IndexError as e:
        return att


def findrec(library: int):
    suggestion = 0
    if library == MOVIE_LIBRARY:
        rand = random.choice(movies['Results'])
        try:
            suggestion = plex.library.section(MOVIE_LIBRARY_NAME).search(title=rand[0], year=rand[1])[0]
        except:
            return "Oops, something went wrong. Want to try again?", None, None, None
    else:
        rand = random.choice(shows['Results'])
        try:
            suggestion = plex.library.section(TV_SHOW_LIBRARY_NAME).search(title=rand[0], year=rand[1])[0]
        except:
            return "Oops, something went wrong. Want to try again?", None, None, None
    att = discord.Embed(title=str(suggestion.title),
                        url="https://app.plex.tv/desktop#!/server/" + PLEX_SERVER_ID + "/details?key=%2Flibrary%2Fmetadata%2F" + str(
                            suggestion.ratingKey), description="Watch it on " + SERVER_NICKNAME)
    att = getposter(att, str(suggestion.title))
    return "How about " + str(suggestion.title) + "?", att, suggestion


def unwatched(mediaType: str, library: int, username: str):
    library_name = ""
    if library == MOVIE_LIBRARY:
        library_name = MOVIE_LIBRARY_NAME
    else:
        library_name = TV_SHOW_LIBRARY_NAME
    names = []
    ids = []
    for user in request("get_users", None)['response']['data']:
        names.append(user['username'])
        ids.append(user['user_id'])
    try:
        user_id = str(ids[names.index(username)])
    except:
        return "I couldn\'t find that username. Please check and try again.", None, None, None
    watched_titles = []
    for watched_item in \
            request("get_history", "user_id=" + str(user_id) + "&length=10000")['response']['data']['data']:
        watched_titles.append(watched_item["full_title"])
    unwatched_titles = []
    for media in (movies['Results'] if mediaType == "movie" else shows['Results']):
        if not media[0] in watched_titles:
            unwatched_titles.append(media)
    rand = random.choice(unwatched_titles)
    try:
        suggestion = plex.library.section(library_name).search(title=rand[0], year=rand[1])[0]
    except:
        return "Oops, something went wrong. Want to try again?", None, None, None
    att = discord.Embed(title=str(suggestion.title),
                        url="https://app.plex.tv/desktop#!/server/" + PLEX_SERVER_ID + "/details?key=%2Flibrary%2Fmetadata%2F" + str(
                            suggestion.ratingKey), description="Watch it on " + SERVER_NICKNAME)
    att = getposter(att, str(suggestion.title))
    return "How about " + str(suggestion.title) + "?", att, suggestion


def recommend(mediaType, recNew, username):
    library = 0
    if mediaType == "movie":
        library = MOVIE_LIBRARY
    else:
        ibrary = TV_LIBRARY
    if recNew:
        return unwatched(mediaType, library, username)
    else:
        return findrec(library)


def getUserCreds(user_id):
    if exists('{}/{}.json'.format(credentials_folder, str(user_id))):
        crypt.makeTemporaryFile('{}{}.json'.format(credentials_folder, str(user_id)),
                                '{}/{}_temp.json'.format(credentials_folder, str(user_id)))
        creds = crypt.decryptFile('{}/{}_temp.json'.format(credentials_folder, str(user_id))).splitlines()
        os.remove('{}/{}_temp.json'.format(credentials_folder, str(user_id)))
        return {'username': creds[0], 'password': creds[1]}


def saveUserCreds(user_id, username, password):
    text = '{}\n{}'.format(username, password)
    crypt.encryptFile(text, '{}/{}.json'.format(credentials_folder, str(user_id)))


def getMediaItem(title, ratingKey=None, libraryID=None):
    library = plex.library
    if libraryID:
        library = library.sectionByID(str(libraryID))
    results = library.search(title=title)
    if results:
        if ratingKey:  # find exact match
            for item in results:
                if item.ratingKey == ratingKey:
                    return item
        return results[0]  # assume first result is correct
    return None


def getMediaInfo(ratingKey):
    r = requests.get('{}/library/metadata/{}?X-Plex-Token={}'.format(PLEX_URL, str(ratingKey), PLEX_TOKEN)).content
    tree = ET.fromstring(r)
    return tree.get('librarySectionID'), tree[0].get('title')


def getRatingKey(url):
    return str(re.search('metadata%2F(\d*)', url).group(1))


def getUrl(text):
    pattern = '{}\S*'.format(PLEX_URL.replace('.', '\.'))
    return str(re.search(pattern, text).group(0))


def checkPlaylist(playlistName):
    for playlist in plex.playlists():
        if playlist.title == playlistName:
            return playlist
    return None


def urlInMessage(message):
    if PLEX_SERVER_ID in message.content and 'metadata%2F' in message.content:
        return getUrl(message.content)
    if message.embeds:
        for embed in message.embeds:
            if PLEX_SERVER_ID in embed.title and 'metadata%2F' in embed.title:
                return getUrl(embed.title)
            elif PLEX_SERVER_ID in embed.description and 'metadata%2F' in embed.description:
                return getUrl(embed.description)
            elif PLEX_SERVER_ID in embed.description and 'metadata%2F' in embed.url:
                return getUrl(embed.url)
        return None
    return None


class Plex(commands.Cog):

    @tasks.loop(count=1)
    async def getLibraries(self):
        # global shows, movies
        items = defaultdict(list)
        movies.clear()
        shows.clear()
        if not movies:
            media = plex.library.section(MOVIE_LIBRARY_NAME)
            json_data = request('get_library', 'section_id=' + str(MOVIE_LIBRARY))
            count = json_data['response']['data']['count']
            # bar = Bar('Loading movies', max=int(count))
            for results in media.search():
                movies['Results'].append([results.title, results.year])
                # bar.next()
            # bar.finish()
        if not shows:
            media = plex.library.section(TV_SHOW_LIBRARY_NAME)
            json_data = request('get_library', 'section_id=' + str(TV_LIBRARY))
            count = json_data['response']['data']['count']
            # bar = Bar('Loading TV shows', max=int(count))
            for results in media.search():
                shows['Results'].append([results.title, results.year])
                # bar.next()
            # bar.finish()
        print("Libraries updated.")
        print("Plex ready.")

    @commands.group(aliases=["Plex"], pass_context=True)
    async def plex(self, ctx: commands.Context):
        """
        Plex Media Server commands
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")

    @plex.group(name="rec", aliases=["sug", "recommend", "suggest"], pass_context=True)
    async def plex_rec(self, ctx: commands.Context, mediaType: str):
        """
        Movie or show recommendations from Plex
        
        Say 'movie' or 'show'.
        Use 'plex rec <mediaType> new <PlexUsername> for a unwatched recommendation.
        """
        if ctx.invoked_subcommand is None:
            if mediaType.lower() not in ('movie', 'show'):
                await ctx.send("Please try again, indicating either 'movie' or 'show'")
            else:
                await ctx.send("Looking for a " + mediaType + "...")
                async with ctx.typing():
                    res, att, sugg = recommend(mediaType, False, None)
                    if att is not None:
                        await ctx.send(res, embed=att)
                    else:
                        await ctx.send(res)

    @plex_rec.error
    async def plex_rec_error(self, ctx, error):
        await ctx.send("Please indicate either 'movie' or 'show'. Add 'new <username>' for an unseen suggestion.")

    @plex_rec.command(name="new", aliases=["unseen"])
    async def plex_rec_new(self, ctx: commands.Context, PlexUsername: str):
        """
        Get a new movie or show recommendation
        """
        mediaType = "movie" if "movie" in str(ctx.message.content).lower() else (
            "show" if "show" in str(ctx.message.content).lower() else None)
        if not mediaType:
            await ctx.send("Please try again, indicating either 'movie' or 'show'")
        else:
            await ctx.send("Looking for a new " + mediaType + "...")
            async with ctx.typing():
                res, att, sugg = recommend(mediaType, True, PlexUsername)
                if att is not None:
                    await ctx.send(res, embed=att)
                else:
                    await ctx.send(res)

    @plex.command(name="stats", aliases=["statistics"], pass_context=True)
    async def plex_stats(self, ctx: commands.Context, PlexUsername: str):
        """
        Watch time statistics for a user
        """
        user_id = None
        for u in request("get_user_names", None)['response']['data']:
            if u['friendly_name'] == PlexUsername:
                user_id = u['user_id']
                break
        if not user_id:
            await ctx.send("User not found.")
        else:
            embed = discord.Embed(title=PlexUsername + "'s Total Plex Watch Time")
            for i in request("get_user_watch_time_stats", "user_id=" + str(user_id))['response']['data']:
                embed.add_field(name=str(datetime.timedelta(seconds=int(i['total_time']))) + ", " + str(
                    i['total_plays']) + " plays", value=(
                    "Last " + str(i['query_days']) + (" Day " if int(i['query_days']) == 1 else " Days ") if int(
                        i['query_days']) != 0 else "All Time "), inline=False)
            await ctx.send(embed=embed)

    @plex_stats.error
    async def plex_stats_error(self, ctx, error):
        await ctx.send("Please include a Plex username")

    @plex.command(name="size", aliases=["library"], pass_context=True)
    async def plex_size(self, ctx: commands.Context):
        """
        Size of Plex libraries
        """
        embed = discord.Embed(title=SERVER_NICKNAME + " Library Statistics")
        size = 0
        for l in request("get_libraries", None)['response']['data']:
            if l['section_name'] not in ['']:  # Exempt sections from list if needed
                if l['section_type'] == 'movie':
                    size = size + \
                           request("get_library_media_info", "section_id=" + str(l['section_id']))['response'][
                               'data']['total_file_size']
                    embed.add_field(name=str(l['count']) + " movies", value=str(l['section_name']), inline=False)
                elif l['section_type'] == 'show':
                    size = size + \
                           request("get_library_media_info", "section_id=" + str(l['section_id']))['response'][
                               'data']['total_file_size']
                    embed.add_field(name=str(l['count']) + " shows, " + str(l['parent_count']) + " seasons, " + str(
                        l['child_count']) + " episodes", value=str(l['section_name']), inline=False)
                elif l['section_type'] == 'artist':
                    size = size + \
                           request("get_library_media_info", "section_id=" + str(l['section_id']))['response'][
                               'data']['total_file_size']
                    embed.add_field(name=str(l['count']) + " artists, " + str(l['parent_count']) + " albums, " + str(
                        l['child_count']) + " songs", value=str(l['section_name']), inline=False)
        embed.add_field(name='\u200b', value="Total: " + filesize(size))
        await ctx.send(embed=embed)

    @plex.command(name="top", aliases=["pop"], pass_context=True)
    async def plex_top(self, ctx: commands.Context, searchTerm: str, timeRange: int):
        """
        Most popular media or most active users during time range (in days)
        Use 'movies','shows','artists' or 'users'
        """
        embed = discord.Embed(title=(
                                        'Most popular ' + searchTerm.lower() if searchTerm.lower() != 'users' else 'Most active users') + ' in past ' + str(
            timeRange) + (' days' if int(timeRange) > 1 else ' day'))
        count = 1
        if searchTerm.lower() == "movies":
            for m in request("get_home_stats", "time_range=" + str(timeRange) + "&stats_type=duration&stats_count=5")[
                'response']['data'][0]['rows']:
                embed.add_field(name=str(count) + ". " + str(m['title']),
                                value=str(m['total_plays']) + (" plays" if int(m['total_plays']) > 1 else " play"),
                                inline=False)
                count = count + 1
            await ctx.send(embed=embed)
        elif searchTerm.lower() == "shows":
            for m in request("get_home_stats", "time_range=" + str(timeRange) + "&stats_type=duration&stats_count=5")[
                'response']['data'][1]['rows']:
                embed.add_field(name=str(count) + ". " + str(m['title']),
                                value=str(m['total_plays']) + (" plays" if int(m['total_plays']) > 1 else " play"),
                                inline=False)
                count = count + 1
            await ctx.send(embed=embed)
        elif searchTerm.lower() == "artists":
            for m in request("get_home_stats", "time_range=" + str(timeRange) + "&stats_type=duration&stats_count=5")[
                'response']['data'][2]['rows']:
                embed.add_field(name=str(count) + ". " + str(m['title']),
                                value=str(m['total_plays']) + (" plays" if int(m['total_plays']) > 1 else " play"),
                                inline=False)
                count = count + 1
            await ctx.send(embed=embed)
        elif searchTerm.lower() == "users":
            for m in request("get_home_stats", "time_range=" + str(timeRange) + "&stats_type=duration&stats_count=5")[
                'response']['data'][7]['rows']:
                embed.add_field(name=str(count) + ". " + str(m['friendly_name']),
                                value=str(m['total_plays']) + (" plays" if int(m['total_plays']) > 1 else " play"),
                                inline=False)
                count = count + 1
            await ctx.send(embed=embed)
        else:
            ctx.send("Please try again. Use 'movies','shows','artists' or 'users'")

    def selectIcon(self, state):
        switcher = {
            "playing": ":arrow_forward:",
            "paused": ":pause_button:",
            "stopped": ":stop_button:",
            "buffering": ":large_blue_circle:",
        }
        return str(switcher.get(state, ""))

    @plex_top.error
    async def plex_top_error(self, ctx, error):
        await ctx.send("Please include <movies|shows|artists|users> <timeFrame>")

    @plex.command(name="current", aliases=["now"], hidden=True, pass_context=True)
    @commands.has_role(ADMIN_ROLE_NAME)
    async def plex_now(self, ctx: commands.Context):
        """
        Current Plex activity
        """
        embed = discord.Embed(title="Current Plex activity")
        json_data = request("get_activity", None)
        try:
            stream_count = json_data['response']['data']['stream_count']
            transcode_count = json_data['response']['data']['stream_count_transcode']
            total_bandwidth = json_data['response']['data']['total_bandwidth']
            lan_bandwidth = json_data['response']['data']['lan_bandwidth']
            overview_message = "Sessions: " + str(stream_count) + (
                " stream" if int(stream_count) == 1 else " streams") + ((" (" + str(transcode_count) + (
                " transcode" if int(transcode_count) == 1 else " transcodes") + ")") if int(
                transcode_count) > 0 else "") + ((" | Bandwidth: " + str(
                round(Decimal(float(total_bandwidth) / 1024), 1)) + " Mbps" + ((" (LAN: " + str(
                round(Decimal(float(lan_bandwidth) / 1024), 1)) + " Mbps)") if int(lan_bandwidth) > 0 else "")) if int(
                total_bandwidth) > 0 else "")
            sessions = json_data['response']['data']['sessions']
            count = 0
            final_message = overview_message + "\n"
            for session in sessions:
                try:
                    count = count + 1
                    stream_message = "**(" + str(count) + ")** " + self.selectIcon(str(session['state'])) + " " + str(
                        session['username']) + ": *" + str(session["full_title"]) + "*\n"
                    stream_message = stream_message + "__Player__: " + str(session['product']) + " (" + str(
                        session['player']) + ")\n"
                    stream_message = stream_message + "__Quality__: " + str(session['quality_profile']) + " (" + (
                        str(round(Decimal(float(session['bandwidth']) / 1024), 1)) if session[
                                                                                          'bandwidth'] is not "" else "O") + " Mbps)" + (
                                         " (Transcode)" if str(
                                             session['stream_container_decision']) == 'transcode' else "")
                    final_message = final_message + "\n" + stream_message + "\n"
                    session_ids.append(str(session['session_id']))
                except ValueError:
                    session_ids.append("000")
                    pass
            print(final_message)
            if int(stream_count) > 0:
                sent_message = await ctx.send(final_message + "\nTo terminate a stream, react with the stream number.")
                for i in range(count):
                    await sent_message.add_reaction(emoji_numbers[i])
                manage_streams = True
                while manage_streams:
                    def check(reaction, user):
                        return user != sent_message.author

                    try:
                        reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                        if reaction and str(reaction.emoji) in emoji_numbers:
                            try:
                                loc = emoji_numbers.index(str(reaction.emoji))
                                request('terminate_session',
                                        'session_id=' + str(session_ids[loc]) + '&message=' + str(
                                            terminate_message))
                                end_notification = await ctx.send(content="Stream " + str(loc + 1) + " was ended.")
                                await end_notification.delete(delay=1.0)
                            except:
                                end_notification = await ctx.send(content="Something went wrong.")
                                await end_notification.delete(delay=1.0)
                    except asyncio.TimeoutError:
                        await sent_message.delete()
                        manage_streams = False
            else:
                await ctx.send("No current activity.")
        except KeyError:
            await ctx.send("**Connection error.**")

    @plex.command(name="new", alias=["added"], pass_context=True)
    async def plex_new(self, ctx: commands.Context):
        """
        See recently added content
        """
        e = discord.Embed(title="Recently Added to " + str(SERVER_NICKNAME))
        count = 5
        cur = 0
        recently_added = request("get_recently_added", "count=" + str(count))
        url = TAUTULLI_BASE_URL + "/api/v2?apikey=" + TAUTULLI_API_KEY + "&cmd=pms_image_proxy&img=" + \
              recently_added['response']['data']['recently_added'][cur]['thumb']
        e.set_image(url=url)
        listing = recently_added['response']['data']['recently_added'][cur]
        e.description = "(" + str(cur + 1) + "/" + str(count) + ") " + str(
            listing['grandparent_title'] if listing['grandparent_title'] != "" else (
                listing['parent_title'] if listing['parent_title'] != "" else listing[
                    'full_title'])) + " - [Watch Now](https://app.plex.tv/desktop#!/server/" + PLEX_SERVER_ID + "/details?key=%2Flibrary%2Fmetadata%2F" + str(
            recently_added['response']['data']['recently_added'][cur]['rating_key']) + ")"
        ra_embed = await ctx.send(embed=e)
        nav = True
        while nav:
            def check(reaction, user):
                return user != ra_embed.author

            try:
                if cur == 0:
                    await ra_embed.add_reaction(u"\u27A1")  # arrow_right
                elif cur == count - 1:
                    await ra_embed.add_reaction(u"\u2B05")  # arrow_left
                else:
                    await ra_embed.add_reaction(u"\u2B05")  # arrow_left
                    await ra_embed.add_reaction(u"\u27A1")  # arrow_right
                reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
            except asyncio.TimeoutError:
                await ra_embed.delete()
                nav = False
                request("delete_image_cache", None)
            else:
                if reaction.emoji == u"\u27A1":
                    if (cur + 1 < count):
                        cur = cur + 1
                        url = TAUTULLI_BASE_URL + "/api/v2?apikey=" + TAUTULLI_API_KEY + "&cmd=pms_image_proxy&img=" + \
                              recently_added['response']['data']['recently_added'][cur]['thumb']
                        e.set_image(url=url)
                        listing = recently_added['response']['data']['recently_added'][cur]
                        e.description = "(" + str(cur + 1) + "/" + str(count) + ") " + str(
                            listing['grandparent_title'] if listing['grandparent_title'] != "" else (
                                listing['parent_title'] if listing['parent_title'] != "" else listing[
                                    'full_title'])) + " - [Watch Now](https://app.plex.tv/desktop#!/server/" + PLEX_SERVER_ID + "/details?key=%2Flibrary%2Fmetadata%2F" + str(
                            recently_added['response']['data']['recently_added'][cur]['rating_key']) + ")"
                        await ra_embed.edit(embed=e)
                        await ra_embed.clear_reactions()
                else:
                    if (cur - 1 >= 0):
                        cur = cur - 1
                        url = TAUTULLI_BASE_URL + "/api/v2?apikey=" + TAUTULLI_API_KEY + "&cmd=pms_image_proxy&img=" + \
                              recently_added['response']['data']['recently_added'][cur]['thumb']
                        e.set_image(url=url)
                        listing = recently_added['response']['data']['recently_added'][cur]
                        e.description = "(" + str(cur + 1) + "/" + str(count) + ") " + str(
                            listing['grandparent_title'] if listing['grandparent_title'] != "" else (
                                listing['parent_title'] if listing['parent_title'] != "" else listing[
                                    'full_title'])) + " - [Watch Now](https://app.plex.tv/desktop#!/server/" + PLEX_SERVER_ID + "/details?key=%2Flibrary%2Fmetadata%2F" + str(
                            recently_added['response']['data']['recently_added'][cur]['rating_key']) + ")"
                        await ra_embed.edit(embed=e)
                        await ra_embed.clear_reactions()

    @plex.command(name="search", alias=["find"], pass_context=True)
    async def plex_search(self, ctx: commands.Context, *, searchTerm: str):
        """
        Search for Plex content
        """
        json_data = request("search", "query=" + searchTerm)['response']['data']
        embed = discord.Embed(title="'" + searchTerm + "' Search Results")
        if json_data['results_count'] > 0:
            for k, l in json_data['results_list'].items():
                results = ""
                results_list = []
                if k.lower() not in ['episode']:  # ignore episode titles
                    for r in l:
                        if searchTerm.lower() in str(r['title']).lower():
                            if r['title'] in results_list or k == 'collection':
                                results_list.append(r['title'] + " - " + r['library_name'])
                                results = results + "[" + r['title'] + " - " + r[
                                    'library_name'] + "](https://app.plex.tv/desktop#!/server/" + PLEX_SERVER_ID + "/details?key=%2Flibrary%2Fmetadata%2F" + str(
                                    r['rating_key']) + ")" + "\n"
                            else:
                                results_list.append(r['title'])
                                results = results + "[" + r[
                                    'title'] + "](https://app.plex.tv/desktop#!/server/" + PLEX_SERVER_ID + "/details?key=%2Flibrary%2Fmetadata%2F" + str(
                                    r['rating_key']) + ")" + "\n"
                    if results != "":
                        embed.add_field(name=k.capitalize() + ("s" if len(results_list) > 1 else ""),
                                        value=str(results), inline=False)
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if reaction.emoji == '✅':
            username = db.find_user_in_db('Plex', user.id)[0]
            if username:
                url = urlInMessage(reaction.message)
                if url:
                    ratingKey = getRatingKey(url)
                    libraryID, title = getMediaInfo(ratingKey)
                    mediaItem = getMediaItem(title, ratingKey, libraryID)
                    if mediaItem:
                        playlist_title = subscriber_playlist_title.format(username) if mediaItem.type in ['artist', 'album', 'track'] else subscriber_playlist_title.format(username)
                        try:
                            playlist = checkPlaylist(playlist_title)
                            if playlist:
                                already = False
                                for item in playlist.items():
                                    if str(item.ratingKey) == str(ratingKey):
                                        await reaction.message.channel.send("That item is already on your {}list".format('play' if mediaItem.type in ['artist','track','album'] else 'watch'))
                                        already = True
                                        break
                                if not already:
                                    playlist.addItems([mediaItem])
                                    await reaction.message.channel.send("Item added to your {}list".format('play' if mediaItem.type in ['artist','track','album'] else 'watch'))
                            else:
                                plex.createPlaylist(title=playlist_title, items=[mediaItem])
                                await reaction.message.channel.send("New {}list created and item added.".format('play' if mediaItem.type in ['artist', 'track', 'album'] else 'watch'))
                        except Exception as e:
                            print(e)
                            await reaction.message.channel.send("Sorry, something went wrong when trying to add this item to your playlist.")
                    else:
                        await reaction.message.channel.send("Sorry, I can't find that item.")

    def __init__(self, bot):
        self.bot = bot
        print("Plex - updating libraries...")
        self.getLibraries.start()
