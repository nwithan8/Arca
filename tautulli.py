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

class Tautulli(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    def request(self, cmd, params):
        return json.loads(requests.get(TAUTULLI_BASE_URL + "/api/v2?apikey=" + TAUTULLI_API_KEY + "&" + str(params) + "&cmd=" + str(cmd)).text if params != None else requests.get(TAUTULLI_BASE_URL + "/api/v2?apikey=" + TAUTULLI_API_KEY + "&cmd=" + str(cmd)).text)
    
    async def embed(self, ctx, json_data):
        await ctx.send(embed=discord.Embed(description=json.dumps(json_data,sort_keys=True,indent=2)))
    
    @commands.group(name="tautulli", aliases=["plexpy"],pass_context=True)
    async def tautulli(self, ctx: commands.Context):
        """
        Make Tautulli API calls
        """
        if ctx.invoked_subcommand is None:
            pass
        
    @tautulli.command(pass_context=True)
    async def add(self, ctx: commands.Context, agent: str, id: int):
        """
        add_newsletter/notifier_config
        Required: agent_id (int)
        Optional: None
        Returns: None
        """
        if agent == "newsletter" or agent == "notifier":
            self.request("add_"+agent+"_config","agent_id="+str(id))
            
    @tautulli.command(pass_context=True)
    async def arnold(self, ctx: commands.Context):
        """
        Get to the chopper!
        """
        await ctx.send(self.request("arnold",None)['response']['data'])
        
    @tautulli.command(pass_context=True)
    async def backup(self, ctx: commands.Context, fileType: str):
        """
        backup_config/db
        """
        if fileType == "db" or fileType == "config":
            self.request("backup_"+fileType,None)
            
    @tautulli.group(name="delete",pass_context=True)
    async def delete(self, ctx: commands.Context):
        """
        Delete commands
        """
        if ctx.invoked_subcommand is None:
            pass
        
    @delete.group(name="history",pass_context=True)
    async def delete_history(self, ctx: commands.Context):
        """
        
        """
        if ctx.invoked_subcommand is None:
            pass
        
    @delete_history.command(name="user",pass_context=True)
    async def delete_history_user(self, ctx: commands.Context, user_id: str):
        """
        delete_all_user_history
        Required: user_id (str)
        Optional: None
        Returns: None
        """
        self.request("delete_all_user_history","user_id="+str(user_id))
        
    @delete_history.command(name="library",pass_context=True)
    async def delete_history_library(self, ctx: commands.Context, section_id: str):
        """
        delete_all_library_history
        Required: section_id (str)
        Optional: None
        Returns: None
        """
        self.request("delete_all_library_history","section_id="+str(section_id))
    
    @delete.group(name="images",pass_context=True)
    async def delete_images(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            pass
        
    @delete_images.command(name="cache",pass_context)
    async def delete_images_cache(self, ctx: commands.Context):
        """
        delete_image_cache
        """
        self.request("delete_image_cache",None)
        
    @delete_images.command(name="hosted",pass_context=True)
    async def delete_images_hosted(self, ctx: commands.Context, rating_key: int, service: str, delete_all: bool):
        """
        delete_hosted_images
        Required: None
        Optional: rating_key (str)
            service (str)
            delete_all (bool)
        Returns: json
        """
        opt_args = ""
        if str(rating_key).lower() != "none":
            opt_args = opt_args + "rating_key="+st(rating_key) + "&"
        if str(service).lower() != "none":
            opt_args = opt_args + "service="+str(service) + "&"
        if str(delete_all).lower() in ['true','false']:
            opt_args = opt_args + "delete_all="+str(delete_all).lower() + "&"
        opt_args = opt_args[:-1]
        await self.embed(ctx, self.request("delete_hosted_images",opt_args))
        
    @delete.command(name="library",pass_context=True)
    async def delete_library(self, ctx: commands.Context, section_id: str):
        """
        delete_library
        Required: section_id (str)
        Optional: None
        Returns: None
        """
        self.request("delete_library","section_id="+str(section_id))
        
    @delete.command(name="device",pass_context=True)
    async def delete_device(self, ctx: commands.Context, mobile_device_id: str):
        """
        delete_mobile_device
        Required: mobile_device_id (str)
        Optional: None
        Returns: None
        """
        self.request("delete_mobile_device","mobile_device_id="+str(mobile_device_id))
        
    @delete.command(name="newsletter",pass_context=True)
    async def delete_newslettter(self, ctx: commands.Context, newsletter_id: int):
        """
        delete_newslettter
        Required: newsletter_id (int)
        Optional: None
        Returns: None
        """
        self.request("delete_newslettter","newsletter_id="+str(newsletter_id))
        
    @delete.command(name="notifier",pass_context=True)
    async def delete_notifier(self, ctx: commands.Context, notifier_id: int):
        """
        delete_notifier
        Required: notifier_id (int)
        Optional: None
        Returns: None
        """
        self.request("delete_notifier","notifier_id="notifier_id)
        
    @delete.command(name="user",pass_context=True)
    async def delete_user(self, ctx: commands.Context, user_id: str):
        """
        delete_user
        Required: user_id (str)
        Optional: None
        Returns: None
        """
        self.request("delete_user","user_id="+str(user_id))
        
    @delete.command(name="temp",pass_context=True)
    async def delete_temp(self, ctx: commands.Context):
        """
        delete_temp_sessions
        """
        self.request("delete_temp_sessions",None)
        
    @delete.command(name="lookup",pass_context=True)
    async def delete_lookup(self, ctx: commands.Context, rating_key: int):
        """
        delete_lookup_info
        Required: rating_key (int)
        Optional: None
        Returns: json
        """
        self.request("delete_lookup_info","rating_key="+str(rating_key))
        
    @delete.group(name="cache",pass_context=True)
    async def delete_cache(self, ctx: commands.Context):
        """
        delete_cache
        """
        if ctx.invoked_subcommand is not None:
            pass
        else:
            self.request("delete_cache",None)
        
    @delete_cache.command(name="info",pass_context=True)
    async def delete_cache_info(self, ctx: commands.Context, id: str):
        """
        delete_media_info_cache
        Required: section_id (str)
        Optional: None
        Returns: None
        """
        self.request("delete_media_info_cache","section_id="+str(section_id))
        
    @delete_cache.command(name="image",pass_context=True)
    async def delete_cache_image(self, ctx: commands.Context):
        """
        delete_image_cache
        """
        self.request("delete_image_cache",None)
        
    @delete.command(name="log",pass_context=True)
    async def delete_log(self, ctx: commands.Context, category: str):
        """
        delete_login_log/delete_newslettter_log/delete_notification_log
        Required: None
        Optional: None
        Returns: None
        """
        if category.lower() == "login":
            self.request("delete_login_log",None)
        else if category.lower() == "newsletter":
            self.request("delete_newslettter_log",None)
        else if category.lower() == "notification":
            self.request("delete_notification_log",None)
    
    @tautulli.command(name="docs",pass_context=True)
    async def docs(self, ctx: commands.Context, md: bool):
        """
        
        """
        if md.lower() == "true":
            self.request("docs_md",None)
        else:
            self.request("docs",None)
            
    @tautulli.group(name="download",pass_context=True)
    async def download(self, ctx: commands.Context):
        """
        Download commands
        """
        if ctx.invoked_subcommand is None:
            pass
        
    @download.command(name="config",pass_context=True)
    async def download_config(self, ctx: commands.Context):
        """
        download_config
        """
        self.request("download_config",None)
        
    @download.command(name="database",pass_context=True)
    async def download_database(self, ctx: commands.Context):
        """
        download_database
        """
        self.request("download_database",None)
        
    @download.group(name="log",pass_context=True)
    async def download_log(self, ctx: commands.Context):
        """
        download_log
        """
        if ctx.invoked_subcommand is not None:
            pass
        else:
            self.request("download_log",None)
            
    @download_log.command(name="plex",pass_context=True)
    async def download_log_plex(self, ctx: commands.Context):
        """
        download_plex_log
        """
        self.request("download_plex_log",None)
        
    @tautulli.group(name="edit",pass_context=True)
    async def edit(self, ctx: commands.Context):
        """
        Edit commands
        """
        if ctx.invoked_subcommand is None:
            pass
        
    @edit.command(name="library",pass_context=True)
    async def edit_library(self, ctx: commands.Context, section_id: str, custom_thumb: str, keep_history: int):
        """
        edit_library
        Required: section_id (str)
        Optional: custom_thumb (str)
            keep_history (int)
        Returns: None
        """
        opt_args = ""
        if str(custom_thumb).lower() != "none":
            opt_args = opt_args + "custom_thumb="+st(custom_thumb) + "&"
        if str(keep_history).lower() != "none":
            opt_args = opt_args + "keep_history="+str(keep_history) + "&"
        opt_args = "&" + opt_args[:-1]
        self.request("delete_hosted_images","section_id="+str(section_id)+opt_args)
        
    @edit.command(name="user",pass_context=True)
    async def edit_user(self, ctx: commands.Context, user_id: str, friendly_name: str, custom_thumb: str, keep_history: int, allow_guest: int):
        """
        edit_user
        Required: user_id (str)
        Optional: friendly_name (str)
            custom_thumb (str)
            keep_history (int)
            allow_guest (int)
        Returns: None
        """
        opt_args = ""
        if str(friendly_name).lower() != "none":
            opt_args = opt_args + "friendly_name="+str(friendly_name) + "&"
        if str(custom_thumb).lower() != "none":
            opt_args = opt_args + "custom_thumb="+st(custom_thumb) + "&"
        if str(keep_history).lower() != "none":
            opt_args = opt_args + "keep_history="+str(keep_history) + "&"
        if str(allow_guest).lower() != "none":
            opt_args = opt_args + "allow_guest="+str(allow_guest) + "&"
        opt_args = "&" + opt_args[:-1]
        self.request("delete_hosted_images","user_id="+str(user_id)+opt_args)
        
    @tautulli.group(name="get",pass_context=True)
    async def get(self, ctx: commands.Context):
        """
        Get commands
        """
        if ctx.invoked_subcommand is None:
            pass
        
        

def setup(bot):
    bot.add_cog(Tautulli(bot))
