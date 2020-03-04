"""
Interact with Rclone
Copyright (C) 2020 Nathan Harris
"""

import discord
from discord.ext import commands, tasks
import asyncio
import sys
import time
import platform
import json
from media_server.rclone import settings as settings
import helper.discord_helper as discord_helper
from helper.helper_functions import filesize
from concurrent.futures import ThreadPoolExecutor


def blocking_function():
    print('entering 30-second blocking function')
    time.sleep(1)
    print('sleep has been completed')
    return 'Pong'


class Rclone(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.remotes = []
        print("Rclone, ready to go.")
        self.build.start()

    @tasks.loop(count=1)
    async def build(self):
        self.remotes = await self.create_remotes()

    async def run_rclone_command(self, *command):
        """
        :param command:
        :return: JSON results of executed command
        """
        process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE,
                                                       stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            return stdout.decode().strip()
        else:
            raise Exception("Subprocess failed.")
            return None

    async def create_remotes(self):
        self.remotes = []
        remotes_list = await self.run_rclone_command(
            *["rclone", "listremotes", "--config={}".format(settings.configPath)])
        if remotes_list:
            for remote_name in remotes_list.splitlines():
                self.remotes.append(Remote(remote_name[:-1]))
            return self.remotes

    @commands.group(aliases=["Rclone"], pass_context=True)
    async def rclone(self, ctx: commands.Context):
        """
        Rclone commands
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")

    @rclone.command(name="list", aliases=["remotes"], pass_context=True)
    async def rclone_list(self, ctx: commands.Context):
        """
        List available Rclone remotes
        """
        remotes = ""
        for remote in self.remotes:
            remotes += "-{}\n".format(remote.name)
        embed = discord.Embed(title='Rclone Remotes', description='**{}**'.format(remotes))
        await ctx.send(embed=embed)

    @rclone_list.error
    async def rclone_list_error(self, ctx, error):
        print(error)
        await ctx.send("Sorry, something went wrong.")

    @rclone.command(name="size", pass_context=True)
    async def rclone_size(self, ctx: commands.Context, remote: str):
        remote_front = remote.split(":")[0]
        print(remote_front)
        if remote_front not in [r.name for r in self.remotes]:
            await ctx.send("That is not a valid Rclone remote.")
        else:
            loading_message = await ctx.send("Calculating size, please wait...")
            loop = asyncio.get_event_loop()
            block_return = await loop.run_in_executor(ThreadPoolExecutor(), blocking_function)
            remote_json = await self.run_rclone_command(
                *['rclone', 'size', '--json', '{}'.format(remote), '--config={}'.format(settings.configPath)])
            print(remote_json)
            if remote_json:
                remote_json = json.loads(remote_json)
                await loading_message.edit(content='{remoteName} stats:\n{fileCount} file{plural}\n{size}'.format(
                    remoteName=remote,
                    fileCount=remote_json.get('count', 0),
                    plural=('s' if remote_json.get('count', 0) > 1 else ''),
                    size=filesize(remote_json.get('bytes', 0))
                ))
            else:
                await loading_message.edit(content="Sorry, something went wrong while checking size.")

    @rclone_size.error
    async def rclone_size_error(self, ctx, error):
        print(error)
        await ctx.send("Sorry, something went wrong.")

    @rclone.command(name="ls", aliases=['files'], pass_context=True)
    async def rclone_ls(self, ctx: commands.Context, remote: str):
        remote_front = remote.split(":")[0]
        print(remote_front)
        if remote_front not in [r.name for r in self.remotes]:
            await ctx.send("That is not a valid Rclone remote.")
        else:
            loading_message = await ctx.send("Gathering files, please wait...")
            loop = asyncio.get_event_loop()
            block_return = await loop.run_in_executor(ThreadPoolExecutor(), blocking_function)
            remote_json = await self.run_rclone_command(
                *['rclone', 'lsjson', '{}'.format(remote), '--config={}'.format(settings.configPath)])
            print(remote_json)
            if remote_json:
                remote_json = json.loads(remote_json)
                response = ""
                for file in remote_json[:30]:
                    response += "-*{name}* {size}\n".format(name=file.get('Name'), size=("- " + filesize(file.get('Size', 0)) if file.get('Size', 0) > 0 else ""))
                await loading_message.edit(content=response)
                # await loading_message.edit(content='{remoteName} stats:\n{fileCount} file{plural}\n{size}'.format(
                #    remoteName=remote,
                #    fileCount=remote_json.get('count', 0),
                #    plural=('s' if remote_json.get('count', 0) > 1 else ''),
                #    size=filesize(remote_json.get('bytes', 0))
                # ))
            else:
                await loading_message.edit(content="Sorry, something went wrong while checking size.")

    @rclone_ls.error
    async def rclone_ls_error(self, ctx, error):
        print(error)
        await ctx.send("Sorry, something went wrong.")


class Remote:
    def __init__(self, name):
        self.name = name


def setup(bot):
    bot.add_cog(Rclone(bot))
