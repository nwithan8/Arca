import discord
from discord.ext import commands, tasks
from plexapi.server import PlexServer
from plexapi.myplex import MyPlexServerShare
import plexapi
from collections import defaultdict
import random
from imdbpie import Imdb
from imdbpie import ImdbFacade
import re
import json
import requests
from progress.bar import Bar
import os
import datetime

PLEX_URL = os.environ.get('PLEX_URL')
PLEX_TOKEN = os.environ.get('PLEX_TOKEN')
PLEX_SERVER_ID = os.environ.get('PLEX_SERVER_ID') #after "/server/" in browser UI URL
SERVER_NICKNAME = os.environ.get('PLEX_SERVER_NAME')

#http://[PMS_IP_Address]:32400/library/sections?X-Plex-Token=YourTokenGoesHere
#Use the above link to find the number for each library: composite="/library/sections/NUMBER/composite/..."
MOVIE_LIBRARY = 1 #Might be different for your Plex library
TV_LIBRARY = 2 #Might be different for your Plex library
MOVIE_LIBRARY_NAME='Movies'
TV_SHOW_LIBRARY_NAME='TV Shows'

TAUTULLI_BASE_URL = os.environ.get('TAUTULLI_URL')
TAUTULLI_API_KEY = os.environ.get('TAUTULLI_KEY')
        
plex = PlexServer(PLEX_URL, PLEX_TOKEN)

imdbf = ImdbFacade()
imdb = Imdb()

owner_players = []
emoji_numbers = [u"1\u20e3",u"2\u20e3",u"3\u20e3",u"4\u20e3",u"5\u20e3"]

shows = defaultdict(list)
movies = defaultdict(list)

class Plex(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
                
    def request(self, cmd, params):
        return json.loads(requests.get(TAUTULLI_BASE_URL + "/api/v2?apikey=" + TAUTULLI_API_KEY + "&" + str(params) + "&cmd=" + str(cmd)).text if params != None else requests.get(TAUTULLI_BASE_URL + "/api/v2?apikey=" + TAUTULLI_API_KEY + "&cmd=" + str(cmd)).text)
    
    def getposter(self, att, title):
        try:
            att.set_image(url=str(imdbf.get_title(imdb.search_for_title(title)[0]['imdb_id']).image.url))
            return att
        except IndexError as e:
            return att

    def unwatched(self, mediaType: str, library: int, username: str):
        library_name = ""
        if library == MOVIE_LIBRARY:
            library_name = MOVIE_LIBRARY_NAME
        else:
            library_name = TV_SHOW_LIBRARY_NAME
        names = []
        ids = []
        for user in self.request("get_users", None)['response']['data']:
            names.append(user['username'])
            ids.append(user['user_id'])
        try:
            user_id = str(ids[names.index(username)])
        except:
            return "I couldn\'t find that username. Please check and try again.", None, None, None
        watched_titles = []
        for watched_item in self.request("get_history","user_id=" + str(user_id) + "&length=10000")['response']['data']['data']:
            watched_titles.append(watched_item["full_title"])
        unwatched_titles = []
        for media in (movies['Results'] if mediaType == "movie" else shows['Results']):
            if not media[0] in watched_titles:
               unwatched_titles.append(media)
        rand = random.choice(unwatched_titles)
        try:
            suggestion = plex.library.section(library_name).search(title=rand[0],year=rand[1])[0]
        except:
            return "Oops, something went wrong. Want to try again?", None, None, None
        att = discord.Embed(title=str(suggestion.title), url="https://app.plex.tv/desktop#!/server/" + PLEX_SERVER_ID + "/details?key=%2Flibrary%2Fmetadata%2F" + str(suggestion.ratingKey), description="Watch it on " + SERVER_NICKNAME)
        att = self.getposter(att, str(suggestion.title))
        return "How about " + str(suggestion.title) + "?", att, suggestion

    def findrec(self, library: int):
        suggestion = 0
        if library == MOVIE_LIBRARY:
            rand = random.choice(movies['Results'])
            try:
                suggestion = plex.library.section(MOVIE_LIBRARY_NAME).search(title=rand[0],year=rand[1])[0]
            except:
                return "Oops, something went wrong. Want to try again?", None, None, None
        else:
            rand = random.choice(shows['Results'])
            try:
                suggestion = plex.library.section(TV_SHOW_LIBRARY_NAME).search(title=rand[0],year=rand[1])[0]
            except:
                return "Oops, something went wrong. Want to try again?", None, None, None
        att = discord.Embed(title=str(suggestion.title), url="https://app.plex.tv/desktop#!/server/" + PLEX_SERVER_ID + "/details?key=%2Flibrary%2Fmetadata%2F" + str(suggestion.ratingKey), description="Watch it on " + SERVER_NICKNAME)
        att = self.getposter(att, str(suggestion.title))
        return "How about " + str(suggestion.title) + "?", att, suggestion

    def recommend(self, mediaType, recNew, username):
        library = 0
        if mediaType == "movie":
            library = MOVIE_LIBRARY
        else:
            ibrary = TV_LIBRARY
        if recNew:
            return self.unwatched(mediaType, library, username)
        else:
            return self.findrec(library)
    
    @tasks.loop(count=1)
    async def getLibraries(self):
        #global shows, movies
        print("Updating libraries...")
        items = defaultdict(list)
        movies.clear()
        shows.clear()
        if not movies:
            media = plex.library.section(MOVIE_LIBRARY_NAME)
            json_data = self.request('get_library','section_id='+str(MOVIE_LIBRARY))
            count = json_data['response']['data']['count']
            bar = Bar('Loading movies', max=int(count))
            for results in media.search():
                movies['Results'].append([results.title, results.year])
                bar.next()
            bar.finish()
        if not shows:
            media = plex.library.section(TV_SHOW_LIBRARY_NAME)
            json_data = self.request('get_library','section_id='+str(TV_LIBRARY))
            count = json_data['response']['data']['count']
            bar = Bar('Loading TV shows', max=int(count))
            for results in media.search():
                shows['Results'].append([results.title, results.year])
                bar.next()
            bar.finish()
        print("Libraries updated.")
            
    @commands.Cog.listener()
    async def on_ready(self):
        self.getLibraries.start()
        
    @commands.group(aliases=["Plex"], pass_context=True)
    async def plex(self, ctx: commands.Context):
        """
        Plex Media Server commands
        """
        if ctx.invoked_subcommand is None:
            pass
    
    @plex.group(name="rec",aliases=["sug","recommend","suggest"], pass_context=True)
    async def plex_rec(self, ctx: commands.Context, mediaType: str):
        """
        Movie or show recommendations from Plex
        
        Say 'movie' or 'show'.
        Use 'plex rec <mediaType> new <PlexUsername> for a unwatched recommendation.
        """
        if ctx.invoked_subcommand is None:
            if mediaType.lower() not in ('movie','show'):
                await ctx.send("Please try again, indicating either 'movie' or 'show'")
            else:
                await ctx.send("Looking for a " + mediaType + "...")
                res, att, sugg = self.recommend(mediaType, False, None)
                if att is not None:
                    await ctx.send(res,embed=att)
                else:
                    await ctx.send(res)
    
    @plex_rec.command(name="new",aliases=["unseen"])
    async def plex_rec_new(self, ctx: commands.Context, PlexUsername: str):
        """
        Get a new movie or show recommendation
        """
        mediaType = "movie" if "movie" in str(ctx.message.content).lower() else ("show" if "show" in str(ctx.message.content).lower() else None)
        if not mediaType:
            await ctx.send("Please try again, indicating either 'movie' or 'show'")
        else:
            await ctx.send("Looking for a new " + mediaType + "...")
            res, att, sugg = self.recommend(mediaType, True, PlexUsername)
            if att is not None:
                await ctx.send(res,embed=att)
            else:
                await ctx.send(res)
                
    @plex.command(name="stats",aliases=["statistics"], pass_context=True)
    async def plex_stats(self, ctx: commands.Context, PlexUsername: str):
        """
        Watch time statistics for a user
        """
        user_id = None
        for u in self.request("get_user_names",None)['response']['data']:
            if u['friendly_name'] == PlexUsername:
                user_id = u['user_id']
                break
        if not user_id:
            await ctx.send("User not found.")
        else:
            embed = discord.Embed(title=PlexUsername + "'s Total Plex Watch Time")
            for i in self.request("get_user_watch_time_stats","user_id=" + str(user_id))['response']['data']:
                embed.add_field(name=str(datetime.timedelta(seconds=int(i['total_time']))) +", " + str(i['total_plays']) + " plays",value=("Last " + str(i['query_days']) + (" Day " if int(i['query_days']) == 1 else " Days ") if int(i['query_days']) != 0 else "All Time "),inline=False)
            await ctx.send(embed=embed)

    @plex.command(name="size", pass_context=True)
    async def plex_size(self, ctx: commands.Context):
        """
        Size of Plex libraries
        """
        embed = discord.Embed(title=SERVER_NICKNAME + " Library Statistics")
        for l in self.request("get_libraries",None)['response']['data']:
            if l['section_type'] == 'movie':
                embed.add_field(name=str(l['count']) + " movies",value=str(l['section_name']),inline=False)
            elif l['section_type'] == 'show':
                embed.add_field(name=str(l['count']) + " shows, " + str(l['parent_count']) + " seasons, " + str(l['child_count']) + " episodes",value=str(l['section_name']),inline=False)
            elif l['section_type'] == 'artist':
                embed.add_field(name=str(l['count']) + " artists, " + str(l['parent_count']) + " albums, " + str(l['child_count']) + " songs",value=str(l['section_name']),inline=False)
        await ctx.send(embed=embed)
        
    @plex.command(name="top", aliases=["pop"], pass_context=True)
    async def plex_top(self, ctx: commands.Context, searchTerm: str, timeRange: int):
        """
        Most popular media or most active users during time range (in days)
        Use 'movies','shows','artists' or 'users'
        """
        embed = discord.Embed(title=('Most popular '+searchTerm.lower() if searchTerm.lower() != 'users' else 'Most active users')+' in past '+str(timeRange)+(' days' if int(timeRange) > 1 else ' day')
        count = 1;
        if searchTerm.lower() == "movies":
            for m in self.request("get_home_stats","time_range="+str(timeRange)+"&stats_type=duration&stats_count=5")['response']['data'][0]['rows']:
                embed.add_field(name=str(count)+". "+str(m['title']),value=str(m['total_plays'])+(" plays" if int(m['total_plays']) > 1 else " play"),inline=False)
                count = count+1
            await ctx.send(embed=embed)
        elif searchTerm.lower() == "shows":
            for m in self.request("get_home_stats","time_range="+str(timeRange)+"&stats_type=duration&stats_count=5")['response']['data'][1]['rows']:
                embed.add_field(name=str(count)+". "+str(m['title']),value=str(m['total_plays'])+(" plays" if int(m['total_plays']) > 1 else " play"),inline=False)
                count = count+1
            await ctx.send(embed=embed)
        elif searchTerm.lower() == "artists":
            for m in self.request("get_home_stats","time_range="+str(timeRange)+"&stats_type=duration&stats_count=5")['response']['data'][2]['rows']:
                embed.add_field(name=str(count)+". "+str(m['title']),value=str(m['total_plays'])+(" plays" if int(m['total_plays']) > 1 else " play"),inline=False)
                count = count+1
            await ctx.send(embed=embed)
        elif searchTerm.lower() == "users":
            for m in self.request("get_home_stats","time_range="+str(timeRange)+"&stats_type=duration&stats_count=5")['response']['data'][7]['rows']:
                embed.add_field(name=str(count)+". "+str(m['friendly_name']),value=str(m['total_plays'])+(" plays" if int(m['total_plays']) > 1 else " play"),inline=False)
                count = count+1
            await ctx.send(embed=embed)
        else:
            ctx.send("Please try again. Use 'movies','shows','artists' or 'users'")

def setup(bot):
    bot.add_cog(Plex(bot))
