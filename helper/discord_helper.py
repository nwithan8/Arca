from typing import List

import discord
from discord.ext import commands, tasks
import asyncio


def discord_get(from_items, name: str):
    return discord.utils.get(from_items, name=name)

def get_guild(bot, guild_id: int):
    return bot.get_guild(guild_id)

def get_guild_roles(bot, guild_id: int = None, guild: discord.Guild = None):
    if not guild and not guild_id:
        raise Exception("'Server' and 'Server ID' cannot both be empty.")
    if not guild:
        guild = get_guild(bot=bot, guild_id=guild_id)
    return guild.roles

def get_guild_members(bot, guild_id: int = None, guild: discord.Guild = None):
    if not guild and not guild_id:
        raise Exception("'Server' and 'Server ID' cannot both be empty.")
    if not guild:
        guild = get_guild(bot=bot, guild_id=guild_id)
    return guild.members

def get_users_with_roles(bot, role_names: List[str] = [], guild: discord.Guild = None, guild_id: int = None):
    filtered_members = []
    filtered_roles = []
    if not guild and not guild_id:
        raise Exception("'Server' and 'Server ID' cannot both be empty.")
    if not guild:
        guild = get_guild(bot=bot, guild_id=guild_id)
    for role in guild.roles:
        if role.name in role_names:
            filtered_roles.append(role)
    for member in guild.members:
        if any(x in member.roles for x in filtered_roles):
            filtered_members.append(member)
    return filtered_members

def get_users_without_roles(bot, role_names: List[str] = [], guild = None, guild_id = None):
    filtered_members = []
    filtered_roles = []
    if not guild and not guild_id:
        raise Exception("'Server' and 'Server ID' cannot both be empty.")
    if not guild:
        guild = get_guild(bot=bot, guild_id=guild_id)
    for role in guild.roles:
        if role.name in role_names:
            filtered_roles.append(role)
    for member in guild.members:
        if not any(x in member.roles for x in filtered_roles):
            filtered_members.append(member)
    return filtered_members


def user_has_role(ctx, user: discord.Member, role_name: str) -> bool:
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

def get_user(user_id: int, ctx: commands.Context) -> discord.Member:
    return ctx.message.guild.fetch_member(user_id)

def get_role(role_name: str, guild: discord.Guild):
    return discord_get(from_items=guild.roles, name=role_name)

async def add_user_role(user: discord.Member, role_name: str, reason: str = "None") -> bool:
    role_to_add = discord_get(from_items=user.roles, name=role_name)
    if not role_to_add:
        return False
    await user.add_roles(role_to_add, reason=reason)
    return True

async def remove_user_role(user: discord.Member, role_name: str, reason: str = "None") -> bool:
    role_to_remove = discord_get(from_items=user.roles, name=role_name)
    if not role_to_remove:
        return False
    await user.remove_roles(role_to_remove, reason=reason)
    return True

def mention_user(user_id: int) -> str:
    return f"<@{user_id}>"

def server_id(ctx: commands.Context) -> int:
    return ctx.message.guild.id

def bold(text) -> str:
    return f"**{text}**"

def italic(text) -> str:
    return f"*{text}*"

def underline(text) -> str:
    return f"__{text}__"

def inline_code(text) -> str:
    return f"``{text}``"

def code_block(text) -> str:
    return f"```{text}```"

async def something_went_wrong(ctx: commands.Context):
    await ctx.send("Something went wrong. Please try again later.")

async def send_direct_message(user: discord.Member, message: str):
    await user.create_dm()
    await user.dm_channel.send(message)

def generate_embed(title: str, **kwargs):
    embed = discord.Embed(title=title)
    for name, value in kwargs.items():
        embed.add_field(name=name, value=value, inline=False)
    return embed


emoji_numbers = ["1️⃣", "2️⃣", "3️⃣", "4️⃣" ,"5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]

async def add_emoji_number_reactions(message: discord.Message, count: int):
    """
    Add number reactions to a message for user interaction
    :param message: message to add emojis to
    :param count: how many emojis to add
    :return: None
    """

    if count <= 0:
        return

    # Only add reactions if necessary, and remove unnecessary reactions
    cache_msg = await message.channel.fetch_message(message.id)
    msg_emoji = [str(r.emoji) for r in cache_msg.reactions]

    emoji_to_remove = []

    for i,e in enumerate(msg_emoji):
        if i >= count or i != emoji_numbers.index(e):
            emoji_to_remove.append(e)

    # if all reactions need to be removed, do it all at once
    if len(emoji_to_remove) == len(msg_emoji):
        await message.clear_reactions()
        msg_emoji = []
    else:
        for e in emoji_to_remove:
            await message.clear_reaction(e)
            del(msg_emoji[msg_emoji.index(e)])

    for i in range(0, count):
        if emoji_numbers[i] not in msg_emoji:
            await message.add_reaction(emoji_numbers[i])