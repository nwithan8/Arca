import discord
from discord.ext import commands, tasks
import asyncio


def get_users_with_roles(bot, roleNames=[], guild=None, guildID=None):
    filtered_members = []
    filtered_roles = []
    if not guild and not guildID:
        raise Exception("'Server' and 'Server ID' cannot both be empty.")
        return None
    if guild:
        guildID = guild.id
    allRoles = bot.get_guild(int(guildID)).roles
    for role in allRoles:
        if role.name in roleNames:
            filtered_roles.append(role)
    for member in bot.get_guild(int(guildID)).members:
        if any(x in member.roles for x in filtered_roles):
            filtered_members.append(member)
    return filtered_members


def get_users_without_roles(bot, roleNames=[], guild=None, guildID=None):
    filtered_members = []
    filtered_roles = []
    if not guild and not guildID:
        raise Exception("'Server' and 'Server ID' cannot both be empty.")
        return None
    if guild:
        guildID = guild.id
    allRoles = bot.get_guild(int(guildID)).roles
    for role in allRoles:
        if role.name in roleNames:
            filtered_roles.append(role)
    for member in bot.get_guild(int(guildID)).members:
        if not any(x in member.roles for x in filtered_roles):
            filtered_members.append(member)
    return filtered_members


def user_has_role(ctx, user, role_name):
    """
    Check if user has a role
    :param ctx: commands.Context
    :param user: User object
    :param role_name: str
    :return: True/False
    """
    role = discord.utils.get(ctx.message.guild.roles, name=role_name)
    if role in user.roles:
        return True
    return False