import discord
from discord.ext import commands, tasks
from discord.utils import get
import os
import asyncio

ADMIN_ROLE_NAME = "Admin"

REGULAR_ROLES_AVAILABLE = {
    "Movie Night":['mw','mn','movie']
}
ADMIN_LOCKED_ROLES_AVAILABLE = {
    
}

class Roles(commands.Cog):

    async def add_roles(self, user, request, guild, admin=False):
        roles_added = ""
        for role_name, nicknames in REGULAR_ROLES_AVAILABLE.items():
            for nick in nicknames:
                if nick in request:
                    role = discord.utils.get(guild.roles, name=role_name)
                    await user.add_roles(role, reason="Self-added")
                    roles_added = roles_added + role_name + ", "
        if admin:
            for role_name, nicknames in ADMIN_LOCKED_ROLES_AVAILABLE.items():
                if nick in request:
                    role = discord.utils.get(guild.roles, name=role_name)
                    await user.add_roles(role, reason="Self-added")
                    roles_added = roles_added + role_name + ", "
        return roles_added
    
    async def remove_roles(self, user, request, guild, admin=False):
        roles_removed = ""
        for role_name, nicknames in REGULAR_ROLES_AVAILABLE.items():
            for nick in nicknames:
                if nick in request:
                    role = discord.utils.get(guild.roles, name=role_name)
                    await user.remove_roles(role, reason="Self-added")
                    roles_removed = roles_removed + role_name + ", "
        if admin:
            for role_name, nicknames in ADMIN_LOCKED_ROLES_AVAILABLE.items():
                if nick in request:
                    role = discord.utils.get(guild.roles, name=role_name)
                    await user.remove_roles(role, reason="Self-added")
                    roles_removed = roles_removed + role_name + ", "
        return roles_removed
            
    @commands.group(aliases=["role"], pass_context=True)
    async def roles(self, ctx: commands.Context):
        """
        Manage roles
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")
            
    @roles.command(name="list", pass_context=True)
    async def roles_list(self, ctx: commands.Context):
        """
        List available roles
        """
        roles = ""
        for role_name, nicknames in REGULAR_ROLES_AVAILABLE.items():
            roles = roles + role_name + ", "
        if ADMIN_ROLE_NAME in ctx.author.roles:
            for role_name, nicknames in ADMIN_LOCKED_ROLES_AVAILABLE.items():
                roles = roles + role_name + ", "
        roles = roles[:-2]
        await ctx.send("Available roles:\n" + roles)
    
    @roles.command(name="add", pass_context=True)
    async def roles_add(self, ctx: commands.Context, *, roles: str):
        """
        Assign roles to yourself or others
        Regular users can add multiple roles to themselves
        Admin users can add one role to multiple users
        """
        added = ""
        admin_role = discord.utils.get(ctx.message.guild.roles, name=ADMIN_ROLE_NAME)
        if admin_role in ctx.author.roles:
            if ctx.message.mentions: # add multiple roles to multiple users
                for u in ctx.message.mentions:
                    added = await self.add_roles(u, roles, ctx.message.guild, True)
                if added:
                    await ctx.send("Those users have received the following roles:\n" + added[:-2])
                else:
                    await ctx.send("No roles were added to those users.")
            else: # add multiple roles (admin) to the message author
                added = await self.add_roles(ctx.message.author, roles, ctx.message.guild, True)
                if added:
                    await ctx.send("These roles were assigned to you:\n" + added[:-2])
                else:
                    await ctx.send("No new roles were assigned to you.")
        else: # not an admin, can only add roles (non-admin) to themselves
            added = await self.add_roles(ctx.message.author, roles, ctx.message.guild, False)
            if added:
                await ctx.send("These roles were assigned to you:\n" + added[:-2])
            else:
                await ctx.send("No new roles were assigned to you.")
                
    @roles_add.error
    async def roles_add_error(self, ctx, error):
        await ctx.send("Something went wrong.")
        
    @roles.command(name="remove", pass_context=True)
    async def roles_remove(self, ctx: commands.Context, *, roles: str):
        """
        Remove roles from yourself or others
        Regular users can remove multiple roles from themselves
        Admin users can remove one role from multiple users
        """
        removed = ""
        admin_role = discord.utils.get(ctx.message.guild.roles, name=ADMIN_ROLE_NAME)
        if admin_role in ctx.author.roles:
            if ctx.message.mentions: # remove multiple roles from multiple users
                for u in ctx.message.mentions:
                    removed = await self.remove_roles(u, roles, ctx.message.guild, True)
                if removed:
                    await ctx.send("Those users have lost the following roles:\n" + removed[:-2])
                else:
                    await ctx.send("No roles were removed from those users.")
            else: # remove multiple roles (admin) from the message author
                removed = await self.remove_roles(ctx.message.author, roles, ctx.message.guild, True)
                if removed:
                    await ctx.send("These roles were unassigned to you:\n" + removed[:-2])
                else:
                    await ctx.send("No new roles were unassigned to you.")
        else: # not an admin, can only remove roles (non-admin) from themselves
            removed = await self.remove_roles(ctx.message.author, roles, ctx.message.guild, False)
            if removed:
                await ctx.send("These roles were unassigned to you:\n" + removed[:-2])
            else:
                await ctx.send("No new roles were unassigned to you.")
                
    @roles_remove.error
    async def roles_remove_error(self, ctx, error):
        await ctx.send("Something went wrong.")
    
    def __init__(self, bot):
        self.bot = bot
        print("Roles ready to go!")
        
