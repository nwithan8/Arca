import os
import re
import shutil
import git
from discord.ext import commands

cog_folder = "downloaded_cogs"


def find_file_in_directory(file_name, directory_name):
    for item in os.listdir(directory_name):
        if os.path.isdir("{}/{}".format(directory_name, item)):
            return find_file_in_directory(file_name=file_name, directory_name='{}/{}/'.format(directory_name, item))
        if item == '{}.py'.format(file_name):
            return item


class RepoManager(commands.Cog):

    @commands.Cog.listener()
    async def on_ready(self):
        if not os.path.exists(cog_folder):
            os.mkdir(cog_folder)
        print("Cog Manager ready.")

    @commands.group(aliases=["import"], pass_context=True)
    async def imp(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")

    @imp.command(name="repo", aliases=['download_repo'], pass_context=True)
    async def imp_repo(self, ctx: commands.Context, url: str):
        """
        Add a cog repo (use .git links)
        """
        if not url.endswith(".git"):
            await ctx.send("Please provide a .git URL")
        else:
            folder_name = str(re.search('/(.[^/]*).git$', url).group(1))
            os.mkdir('{}/{}'.format(cog_folder, folder_name))
            print(git.Repo.clone_from(url=url, to_path='{}/{}'.format(cog_folder, folder_name)))


def setup(bot):
    bot.add_cog(RepoManager(bot))
