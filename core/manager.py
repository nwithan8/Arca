import discord
from discord.ext import commands, tasks
import urllib
import os, sys
import git
import shutil
import re

cog_folder = "cogs_dest"

class Manager(commands.Cog):
    
    @commands.Cog.listener()
    async def on_ready(self):
        #self.getLibraries.start()
        print("Cog Manager ready.")
        
    @commands.group(aliases=["import"], pass_context=True)
    async def imp(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            pass
        
    @imp.command(name="add",aliases=['repo'], pass_context=True)
    async def imp_add(self, ctx: commands.Context, url: str):
        """
        Add a cog repo (use .git links)
        """
        folder_name = str(re.search('/(.[^/]*).git$', url).group(1)).lower()
        os.mkdir(os.getcwd() + "/" + folder_name)
        print(git.Repo.clone_from(url=url,to_path=os.getcwd() + "/" + folder_name + "/"))
        
    @imp.command(name="load")
    async def imp_load(self, ctx: commands.Context, repo: str, cogName: str):
        """
        Load a cog from a downloaded repo
        """
        for directory in os.listdir(os.getcwd() + "/" + repo.lower() + "/"):
            if os.path.isdir(os.getcwd() + '/' + repo.lower() + '/' + directory) and not (directory.startswith(".")) and (directory == cogName):
                try:
                    shutil.move(os.getcwd() + "/" + repo.lower() + "/" + directory, os.getcwd() + "/" + cog_folder + "/" + directory)
                    count = 0
                    for item in os.listdir(os.getcwd() + "/" + repo.lower() + "/"):
                        if os.path.isdir(os.getcwd() + "/" + repo.lower() + "/" + item) and not (item.startswith(".")):
                            count = count + 1
                    if count == 0:
                        shutil.rmtree(os.getcwd() + "/" + repo.lower())
                except shutil.Error as e:
                    print("Not copied. Error:\n %s" % e)
                except OSError as e:
                    print("Not copied. Error:\n%s" % e)

def setup(bot):
    bot.add_cog(Manager(bot))
