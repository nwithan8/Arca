"""
Parse RSS feeds for major online media outlets
Copyright (C) 2019 Nathan Harris
"""

from discord.ext import commands, tasks
import discord
import requests
import json
import os

WEBUI_PASSWORD = os.environ.get('DELUGE_PASS')
WEB_URL = os.environ.get('DELUGE_URL') + '/json'

header = {"Accept": "application/json", "Content-Type": "application/json"}

class Deluge(commands.Cog):
    
    session = requests.Session()
    
    def post(self, method, params, use_cookies):
        """
        Params: String method, List params, Bool use_cookies
        Returns: Requests.Response, Bool status_code
        """
        data = {"method": method, "params": params, "id": 1}
        r = self.session.post(WEB_URL, headers=header, data=json.dumps(data), cookies=(self.session.cookies if use_cookies == True else None))
        if str(r.status_code).startswith("2"):
            return r, True
        else:
            return None, False
    
    def login(self):
        # login
        login, passed = self.post("auth.login", [WEBUI_PASSWORD], False)
        if passed:
            self.session.cookies = login.cookies
            # verify connection
            connection, passed = self.post("web.connected", [], 'True')
            if passed and json.loads(connection.text)['result'] == 'True':
                return True
        return False

    def get_torrents(self):
        """
        Params: None
        Returns: JSON-formatted Request.Response
        """
        r, passed = self.post("core.get_torrents_status",[{},""], True)
        if passed:
            return json.loads(r.text)
        return None
    
    @commands.group(pass_context=True, case_insensitive=True)
    async def deluge(self, ctx: commands.Context):
        """
        Interact with Deluge
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")   
            
    @deluge.command(name="torrents", pass_context=True, case_insensitive=True)
    async def deluge_torrents(self, ctx: commands.Context):
        """
        Get Deluge torrents
        """
        torrents = "```"
        data = self.get_torrents()
        for k, v in data['result'].items():
            if v['ratio'] not in ['-1','0']:
                if len(torrents) > 1800:
                    await ctx.send(torrents + "```")
                    torrents = "```"
                else:
                    torrents += "#{queue} | {ratio} | {name} | {id})\n".format(queue=v['queue'], ratio=v['ratio'], name=v['name'], id=v['hash'])
        await ctx.send(torrents + "```")
    
    @deluge.command(name="active", pass_context=True)
    async def deluge_active(self, ctx: commands.Context):
        """
        Get active Deluge torrents
        """
        torrents = "```Queue\t | Progress\t | Name\n"
        data = self.get_torrents()
        for k, v in data['result'].items():
            if float(v['progress']) > 0.0 and float(v['progress']) < 100.0:
                if len(torrents) > 1800:
                    await ctx.send(torrents + "```")
                    torrents = "```"
                else:
                    torrents += "#{queue}\t | {progress}%\t | {name}\n".format(queue=v['queue'], progress=("%.2f" % v['progress']), name=v['name'])
        await ctx.send(torrents + "```")
        
    def __init__(self, bot):
        self.bot = bot
        self.login()
        print("Deluge ready.")


def setup(bot):
    bot.add_cog(Deluge(bot))