import discord
from discord.ext import commands, tasks
from discord.utils import get
import os
from plexapi.server import PlexServer
from plexapi.myplex import MyPlexServerShare
import plexapi
import json
import requests
import asyncio

TAUTULLI_BASE_URL = os.environ.get('TAUTULLI_URL')
TAUTULLI_API_KEY = os.environ.get('TAUTULLI_KEY')
        
PLEX_URL = os.environ.get('PLEX_URL')
PLEX_TOKEN = os.environ.get('PLEX_TOKEN')
PLEX_SERVER_ID = os.environ.get('PLEX_SERVER_ID') #after "/server/" in browser UI URL
SERVER_NICKNAME = os.environ.get('PLEX_SERVER_NAME')

plex = PlexServer(PLEX_URL, PLEX_TOKEN)

class Demo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    def request(self, cmd, params):
        return json.loads(requests.get(TAUTULLI_BASE_URL + "/api/v2?apikey=" + TAUTULLI_API_KEY + "&" + str(params) + "&cmd=" + str(cmd)).text if params != None else requests.get(TAUTULLI_BASE_URL + "/api/v2?apikey=" + TAUTULLI_API_KEY + "&cmd=" + str(cmd)).text)
    
    @commands.command(name="demo")
    @commands.has_role("Admin")
    async def demo(self, ctx: commands.Context):
        e = discord.Embed(title="Recently Added to " + str(SERVER_NICKNAME))
        count = 5
        cur = 0
        recently_added = self.request("get_recently_added","count="+str(count))
        url = TAUTULLI_BASE_URL+"/api/v2?apikey="+TAUTULLI_API_KEY+"&cmd=pms_image_proxy&img="+recently_added['response']['data']['recently_added'][cur]['thumb']
        e.set_image(url=url)
        listing = recently_added['response']['data']['recently_added'][cur]
        e.description = "(" + str(cur+1) + "/" + str(count) + ") " + str(listing['grandparent_title'] if listing['grandparent_title'] != "" else (listing['parent_title'] if listing['parent_title'] != "" else listing['full_title'])) + " - [Watch Now](https://app.plex.tv/desktop#!/server/" + PLEX_SERVER_ID + "/details?key=%2Flibrary%2Fmetadata%2F" + str(recently_added['response']['data']['recently_added'][cur]['rating_key']) + ")"
        ra_embed = await ctx.send(embed=e)
        nav = True
        while nav:
            def check(reaction, user):
                return user != ra_embed.author
            
            try:
                if cur == 0:
                    await ra_embed.add_reaction(u"\u27A1") #arrow_right
                elif cur == count - 1:
                    await ra_embed.add_reaction(u"\u2B05") #arrow_left
                else:
                    await ra_embed.add_reaction(u"\u2B05") #arrow_left
                    await ra_embed.add_reaction(u"\u27A1") #arrow_right
                reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
            except asyncio.TimeoutError:
                await ra_embed.delete()
                nav = False
                self.request("delete_image_cache", None)
            else:
                if reaction.emoji == u"\u27A1":
                    if (cur + 1 < count):
                        cur = cur + 1
                        url = TAUTULLI_BASE_URL+"/api/v2?apikey="+TAUTULLI_API_KEY+"&cmd=pms_image_proxy&img="+recently_added['response']['data']['recently_added'][cur]['thumb']
                        e.set_image(url=url)
                        listing = recently_added['response']['data']['recently_added'][cur]
                        e.description = "(" + str(cur+1) + "/" + str(count) + ") " + str(listing['grandparent_title'] if listing['grandparent_title'] != "" else (listing['parent_title'] if listing['parent_title'] != "" else listing['full_title'])) + " - [Watch Now](https://app.plex.tv/desktop#!/server/" + PLEX_SERVER_ID + "/details?key=%2Flibrary%2Fmetadata%2F" + str(recently_added['response']['data']['recently_added'][cur]['rating_key']) + ")"
                        await ra_embed.edit(embed=e)
                        await ra_embed.clear_reactions()
                else:
                    if (cur - 1 >= 0):
                        cur = cur - 1
                        url = TAUTULLI_BASE_URL+"/api/v2?apikey="+TAUTULLI_API_KEY+"&cmd=pms_image_proxy&img="+recently_added['response']['data']['recently_added'][cur]['thumb']
                        e.set_image(url=url)
                        listing = recently_added['response']['data']['recently_added'][cur]
                        e.description = "(" + str(cur+1) + "/" + str(count) + ") " + str(listing['grandparent_title'] if listing['grandparent_title'] != "" else (listing['parent_title'] if listing['parent_title'] != "" else listing['full_title'])) + " - [Watch Now](https://app.plex.tv/desktop#!/server/" + PLEX_SERVER_ID + "/details?key=%2Flibrary%2Fmetadata%2F" + str(recently_added['response']['data']['recently_added'][cur]['rating_key']) + ")"
                        await ra_embed.edit(embed=e)
                        await ra_embed.clear_reactions()
                    
        
        #for item in recently_added["response"]["data"]["recently_added"]:
            #url = TAUTULLI_BASE_URL+"/api/v2?apikey="+TAUTULLI_API_KEY+"&cmd=pms_image_proxy&img="+item.thumb
        #    url = TAUTULLI_BASE_URL+"/api/v2?apikey="+TAUTULLI_API_KEY+"&cmd=pms_image_proxy&img="+item['thumb']
        #    e.set_image(url=url)
        #await ctx.send(embed=e)

def setup(bot):
    bot.add_cog(Demo(bot))
