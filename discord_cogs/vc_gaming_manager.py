# Thanks to https://github.com/windfreaker for this script

from discord import ActivityType
from discord.ext import commands


def name_generator(channel):
    game_names = []
    for member in channel.members:
        for activity in member.activities:
            if activity.type is ActivityType.playing:
                game_names.append(activity.name)
    if len(game_names) == 0:
        return 'No Game Detected'
    elif len(game_names) == 1:
        return game_names[0]
    else:
        counter = 0
        prev_name = game_names[0]
        for name in game_names:
            if channel.name.startswith(name):
                prev_name = name
            else:
                counter += 1
        if counter != 0:
            return f'{prev_name} + {str(counter)}'
        else:
            return prev_name


async def channel_joined(member, channel):
    if activator_checklist(channel):
        new_name = name_generator(channel)
        await channel.clone(reason=str(member) + ' joined activator channel')
        await channel.edit(name=new_name, user_limit=0)
    elif activated_checklist(channel):
        updated_name = name_generator(channel)
        await channel.edit(name=updated_name)


async def channel_left(member, channel):
    if activated_checklist(channel):
        if len(channel.members) == 0:
            await channel.delete(reason=str(member) + ' left activated channel')
        else:
            updated_name = name_generator(channel)
            await channel.edit(name=updated_name)


def activator_checklist(channel):
    if channel is None:
        return False
    afk_vc = channel.guild.afk_channel
    if channel.bitrate == 64000 and channel.user_limit == 1 and channel.name == 'Join to Talk':
        if len(channel.members) != 1:
            return False
        elif afk_vc is None:
            return True
        elif channel.id != afk_vc.id:
            return True
    return False


def activated_checklist(channel):
    if channel is None:
        return False
    if channel.bitrate == 64000 and channel.user_limit != 1 and channel.name != 'Join to Talk' and channel.category_id == 588935560400338964:
        return True
    return False


@commands.Cog.listener()
async def on_voice_state_update(member, before, after):
    await channel_left(member, before.channel)
    await channel_joined(member, after.channel)


@commands.Cog.listener()
async def on_member_update(before, after):
    if before.activities != after.activities:
        if after.voice is not None:
            if activated_checklist(after.voice.channel):
                updated_name = name_generator(after.voice.channel)
                await after.voice.channel.edit(name=updated_name)


def setup(bot):
    bot.add_listener(on_voice_state_update)
    bot.add_listener(on_member_update)
