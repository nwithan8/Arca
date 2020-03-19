import discord
from discord.ext import commands, tasks
from discord.ext.commands import ExtensionAlreadyLoaded, ExtensionNotLoaded, ExtensionNotFound
import os
import re
import git

USE_DROPBOX = False
USE_REMOTE_CONFIG = False
if USE_DROPBOX:
    import helper.dropbox_handler as dropbox

DOWNLOADED_REPOS_FOLDER = 'cog_repos'


class CogHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="list")
    @commands.is_owner()
    async def cogs_list(self, ctx: commands.Context):
        """
        List all available cogs
        """
        pass

    @commands.command(name="enable", aliases=["load"])
    @commands.is_owner()
    async def cogs_enable(self, ctx: commands.Context, cog: str):
        """
        Load a cog (folder.file)
        """
        try:
            self.bot.load_extension(cog)
            await ctx.send("{} has been enabled.".format(cog))
            if USE_REMOTE_CONFIG:
                edit_remote_config("cogs.txt", cog_to_add=cog)
        except ExtensionNotFound:
            try:
                cog = '{}.py'.format(cog.replace(".", "/"))
                if USE_DROPBOX:
                    dropbox.download_file(cog)
                self.bot.load_extension(cog)
                await ctx.send("{} has been enabled.".format(cog))
            except Exception as e:
                print(e)
                await ctx.send("That extension could not be found locally or on Dropbox.")
        except ExtensionAlreadyLoaded:
            await ctx.send("Extension already enabled.")
        except Exception as e:
            print(e)
            await ctx.send("Something went wrong.")

    @commands.command(name="disable", aliases=["unload"])
    @commands.is_owner()
    async def cogs_disable(self, ctx: commands.Context, cog: str):
        """
        Unload a cog (folder.file)
        """
        try:
            self.bot.unload_extension(cog)
            await ctx.send("{} has been disabled.".format(cog))
            if USE_REMOTE_CONFIG:
                edit_remote_config("cogs.txt", cog_to_remove=cog)
        except ExtensionNotLoaded:
            await ctx.send("That extension is not active.")
        except:
            await ctx.send("Something went wrong.")

    @commands.command(name="restart", aliases=["reload"])
    @commands.is_owner()
    async def cogs_restart(self, ctx: commands.Context, cog: str):
        """
        Reload a cog (folder.file)
        """
        try:
            self.bot.reload_extension(cog)
            await ctx.send("{} has been reloaded".format(cog))
        except ExtensionNotLoaded:
            await ctx.send("That extension is not active.")
        except:
            await ctx.send("Something went wrong.")

    @commands.command(name="download")
    @commands.is_owner()
    async def cogs_download(self, ctx: commands.Context, cog: str):
        """
        Download a cog from Dropbox
        """
        if USE_DROPBOX:
            try:
                cog = '{}.py'.format(cog.replace(".", "/"))
                if USE_DROPBOX:
                    dropbox.download_file(cog)
                await ctx.send("{} has been downloaded".format(cog))
            except:
                await ctx.send("Sorry, I couldn't download that file.")
        else:
            await ctx.send("Dropbox use is not enabled.")

    @commands.command(name="upload")
    @commands.is_owner()
    async def cogs_upload(self, ctx: commands.Context, cog: str):
        """
        Upload a local cog to Dropbox
        """
        if USE_DROPBOX:
            try:
                path = cog.replace(".", "/")
                folderPath = '/'.join(path.split('/')[:-1])
                if dropbox.create_folder_path(folderPath):
                    cog = '{}.py'.format(path)
                    print(cog)
                    dropbox.upload_file(cog, rename=cog)
                    await ctx.send("{} has been uploaded".format(cog))
                else:
                    await ctx.send("Sorry, something went wrong creating the folder path on Dropbox.")
            except Exception as e:
                print(e)
                await ctx.send("Sorry, I couldn't upload that file.")
        else:
            await ctx.send("Dropbox use is not enabled.")

    @commands.command(name="repo")
    @commands.is_owner()
    async def cogs_repo(self, ctx: commands.Context, url: str):
        """
        Add a cog repo (use .git links)
        """
        if not url.endswith(".git"):
            await ctx.send("Please provide a .git URL")
        else:
            try:
                folder_name = str(re.search('/(.[^/]*).git$', url).group(1))
                os.mkdir('{}/{}'.format(DOWNLOADED_REPOS_FOLDER, folder_name))
                repo = git.Repo.clone_from(url=url, to_path='{}/{}'.format(DOWNLOADED_REPOS_FOLDER, folder_name))
                if repo:
                    await ctx.send("Repository has been cloned. Cogs available in {}.{}".format(DOWNLOADED_REPOS_FOLDER, folder_name))
                else:
                    await ctx.send("Repository could not be cloned.")
            except Exception as e:
                print(e)
                await ctx.send("Something went wrong.")


def is_valid_cog(cog_path):
    if os.path.exists(cog_path):
        return True
    return False


def load_remote_config(filename):
    dropbox.download_file(filename)
    cogs = []
    with open(filename, 'r') as f:
        for line in f:
            cogs.append(line.strip())
    return cogs


def edit_remote_config(filename, cog_to_add=None, cog_to_remove=None):
    current_cogs = load_remote_config(filename)
    if cog_to_add and cog_to_add not in current_cogs:
        current_cogs.append(cog_to_add)
    if cog_to_remove and cog_to_remove in current_cogs:
        current_cogs.remove(cog_to_remove)
    with open(filename, 'w') as f:
        for cog in current_cogs:
            f.write(cog + "\n")
    dropbox.upload_file(filename)


def setup(bot):
    bot.add_cog(CogHandler(bot))
