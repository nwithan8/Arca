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

def bold(text):
    return f"**{text}**"

def italic(text):
    return f"*{text}*"

def underline(text):
    return f"__{text}__"

def inline_code(text):
    return f"``{text}``"

def code_block(text):
    return f"```{text}```"


emoji_numbers = ["1️⃣", "2️⃣", "3️⃣", "4️⃣" ,"5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]

async def add_emoji_number_reactions(message, count):
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