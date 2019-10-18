import discord
from discord.ext import commands
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

class PlexRecs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
                    
    @commands.group()
    async def plexrec(self, ctx, *, message):
        PLEX_URL = os.environ.get('PLEX_URL')
        PLEX_TOKEN = os.environ.get('PLEX_TOKEN')
        PLEX_SERVER_ID = '26b7b19caa9169fce158fc867a4d0582e3a00cfc' #after "/server/" in browser UI URL
        SERVER_NICKNAME = 'BigBox Media'

        #http://[PMS_IP_Address]:32400/library/sections?X-Plex-Token=YourTokenGoesHere
        #Use the above link to find the number for each library: composite="/library/sections/NUMBER/composite/..."
        MOVIE_LIBRARY = 1 #Might be different for your Plex library
        TV_LIBRARY = 2 #Might be different for your Plex library
        MOVIE_LIBRARY_NAME=''
        TV_SHOW_LIBRARY_NAME=''

        TAUTULLI_BASE_URL = os.environ.get('TAUTULLI_URL')
        TAUTULLI_API_KEY = os.environ.get('TAUTULLI_KEY')
        
        plex = PlexServer(PLEX_URL, PLEX_TOKEN)
        
        shows = defaultdict(list)
        movies = defaultdict(list)

        imdbf = ImdbFacade()
        imdb = Imdb()

        owner_players = []
        emoji_numbers = [u"1\u20e3",u"2\u20e3",u"3\u20e3",u"4\u20e3",u"5\u20e3"]
        
        async def request(cmd, params):
            return requests.get(TAUTULLI_BASE_URL + "/api/v2?apikey=" + TAUTULLI_API_KEY + "&" + str(params) + "&cmd=" + str(cmd)) if params != None else requests.get(TAUTULLI_BASE_URL + "/api/v2?apikey=" + TAUTULLI_API_KEY + "&cmd=" + str(cmd))
        
        async def getlibrary(library):
            global shows, movies
            items = defaultdict(list)
            media = plex.library.section(MOVIE_LIBRARY_NAME) if library == MOVIE_LIBRARY else plex.library.section(TV_SHOW_LIBRARY_NAME)
            if library == MOVIE_LIBRARY:
                if not movies:
                    json_data = json.loads(request("get_library", "section_id=" + str(MOVIE_LIBRARY)).text)
                    count = json_data['response']['data']['count']
                    bar = Bar('Loading movies', max=int(count))
                    for results in media.search():
                        movies['Results'].append([results.title, results.year])
                        bar.next()
                    bar.finish()
            else:
                if not shows:
                    json_data = json.loads(request("get_library", "section_id=" + str(TV_LIBRARY)).text)
                    count = json_data['response']['data']['count']
                    bar = Bar('Loading TV shows', max=int(count))
                    for results in media.search():
                        shows['Results'].append([results.title, results.year])
                        bar.next()
                    bar.finish()

        async def getposter(att, title):
            try:
                att.set_image(url=str(imdbf.get_title(imdb.search_for_title(title)[0]['imdb_id']).image.url))
                return att
            except IndexError:
                return att

        async def unwatched(library, username):
            global shows, movies
            media_type = ""
            library_name = ""
            if library == MOVIE_LIBRARY:
                library_name = MOVIE_LIBRARY_NAME
                media_type = "movie"
            else:
                library_name = TV_SHOW_LIBRARY_NAME
                media_type = "show"
            json_data = json.loads(request("get_users", None).text)
            names = []
            ids = []
            for user in json_data['response']['data']:
                names.append(user['username'])
                ids.append(user['user_id'])
            try:
                user_id = str(ids[names.index(username)])
            except:
                return "I couldn\'t find that username. Please check and try again.", None, None, None
            json_data = json.loads(request("get_history","user_id=" + str(user_id) + "&length=10000").text)
            watched_titles = []
            for watched_item in json_data['response']['data']['data']:
                watched_titles.append(watched_item["full_title"])
            unwatched_titles = []
            for media in (movies['Results'] if media_type == "movie" else shows['Results']):
                if not media[0] in watched_titles:
                    unwatched_titles.append(media)
            rand = random.choice(unwatched_titles)
            try:
                suggestion = plex.library.section(library_name).search(title=rand[0],year=rand[1])[0]
            except:
                return "Oops, something went wrong. Want to try again?", None, None, None
            att = discord.Embed(title=str(suggestion.title), url="https://app.plex.tv/desktop#!/server/" + PLEX_SERVER_ID + "/details?key=%2Flibrary%2Fmetadata%2F" + str(suggestion.ratingKey), description="Watch it on " + SERVER_NICKNAME)
            att = await getposter(att, str(suggestion.title))
            return "How about " + str(suggestion.title) + "?", media_type, att, suggestion

        async def findrec(library):
            global shows, movies
            suggestion = 0
            media_type = ""
            if library == MOVIE_LIBRARY:
                rand = random.choice(movies['Results'])
                try:
                    suggestion = plex.library.section(MOVIE_LIBRARY_NAME).search(title=rand[0],year=rand[1])[0]
                except:
                    return "Oops, something went wrong. Want to try again?", None, None, None
                media_type = "movie"
            else:
                rand = random.choice(shows['Results'])
                try:
                    suggestion = plex.library.section(TV_SHOW_LIBRARY_NAME).search(title=rand[0],year=rand[1])[0]
                except:
                    return "Oops, something went wrong. Want to try again?", None, None, None
                media_type = "show"
            att = discord.Embed(title=str(suggestion.title), url="https://app.plex.tv/desktop#!/server/" + PLEX_SERVER_ID + "/details?key=%2Flibrary%2Fmetadata%2F" + str(suggestion.ratingKey), description="Watch it on " + SERVER_NICKNAME)
            att = await getposter(att, str(suggestion.title))
            return "How about " + str(suggestion.title) + "?", media_type, att, suggestion

        async def recommend(message, ctx):
            library = 0
            plex_username = ""
            if "movie" in message.lower() or "tv" in message.lower() or "show" in message.lower():
                if "new" in message.lower():
                    if not "%" in message:
                        return "Please try again. Make sure to include \'%\' followed by your Plex username.", None, None, None
                    else:
                        splitted = str(message).split("%")
                        if "@" in str(splitted[-1:]):
                            plex_username = str(re.findall('[\w\.-]+@[\w\.-]+\.\w+', str(splitted[-1:])))
                        else:
                            plex_username = str(re.findall('[%]\w+', message))[3:]
                        plex_username = plex_username.replace(r"'","")
                        plex_username = plex_username.replace("[","")
                        plex_username = plex_username.replace("]","").strip()
                        if plex_username == "":
                            return "Please try again. Make sure you include '%' directly in front of your Plex username (ex. %myusername).", None, None, None
                await ctx.send("Looking for a recommendation. This might take a sec, please be patient...")
                if "movie" in message.lower():
                    library = MOVIE_LIBRARY
                    if "new" in message.lower():
                        return await unwatched(library, plex_username)
                    else:
                        return await findrec(library)
                elif "tv" in message.lower() or "show" in message.lower():
                    library = TV_LIBRARY
                    if "new" in message.lower():
                        return await unwatched(library, plex_username)
                    else:
                        return await findrec(library)
            else:
                return "Please ask again, indicating if you want a movie or a TV show.\nIf you only want shows or movies you haven\'t seen before, include the word \'new\' and \'%<your Plex username>\'.", None, None, None

        response, media_type, att, sugg = await recommend(message, ctx)
        if att is not None:
            await message.channel.send(response, embed=att)
        else:
            await message.channel.send(response)
    

def setup(bot):
    bot.add_cog(PlexRecs(bot))
