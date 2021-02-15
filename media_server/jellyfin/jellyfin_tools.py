"""
Interact with a Jellyfin Media Server, manage users
Copyright (C) 2019 Nathan Harris
"""

from discord.ext import commands
import asyncio

from helper.decorators import has_admin_role
from media_server.jellyfin import settings as settings
from media_server.jellyfin import jellyfin_api as jf
from media_server.jellyfin import jellyfin_recs as jr

live_session_ids = []
emoji_numbers = [u"1\u20e3", u"2\u20e3", u"3\u20e3", u"4\u20e3", u"5\u20e3", u"6\u20e3", u"7\u20e3", u"8\u20e3",
                 u"9\u20e3"]


def selectIcon(state):
    switcher = {
        "playing": ":arrow_forward:",
        "paused": ":pause_button:",
        "stopped": ":stop_button:",
        "buffering": ":blue_circle:",
    }
    return str(switcher.get(state, ""))


class Jellyfin(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        jf.authenticate()
        print("Jellyfin ready to go.")

    @commands.group(name="jf", aliases=["jellyfin", "JF"], pass_context=True)
    async def jellyfin(self, ctx: commands.Context):
        """
        jellyfin Media Server commands
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")

    @jellyfin.group(name="rec", aliases=["sug", "recommend", "suggest"], pass_context=True)
    async def jellyfin_rec(self, ctx: commands.Context, mediaType: str):
        """
        Movie, show or artist recommendation from jellyfin

        Say 'movie', 'show' or 'artist'
        Use 'jellyfinrec <mediaType> new <jellyfinUsername>' for an unwatched recommendation.
        """
        if ctx.invoked_subcommand is None:
            mediaType = mediaType.lower()
            if mediaType.lower() not in jr.accepted_types:
                acceptedTypes = "', '".join(jr.accepted_types)
                await ctx.send("Please try again, indicating '{}'".format(acceptedTypes))
            else:
                holdMessage = await ctx.send(
                    "Looking for a{} {}...".format("n" if (mediaType[0] in ['a', 'e', 'i', 'o', 'u']) else "",
                                                   mediaType))
                async with ctx.typing():
                    response, embed, mediaItem = jr.make_recommendation(mediaType=mediaType, unwatched=False)
                await holdMessage.delete()
                if embed is not None:
                    recMessage = await ctx.send(response, embed=embed)
                else:
                    await ctx.send(response)
                if mediaItem and mediaItem.type not in ['artist', 'album', 'track']:
                    await recMessage.add_reaction('🎞️')
                    try:
                        def check(trailerReact, trailerReactUser):
                            return trailerReact.emoji == '🎞️' and trailerReactUser.id != self.bot.user.id

                        showTrailer, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                        if showTrailer:
                            await ctx.send(jr.get_trailer_URL(mediaItem=mediaItem))
                    except asyncio.TimeoutError:
                        await recMessage.clear_reactions()

    @jellyfin_rec.error
    async def jellyfin_rec_error(self, ctx, error):
        print(error)
        await ctx.send("Sorry, something went wrong while looking for a recommendation.")

    @jellyfin_rec.command(name="new", aliases=["unseen", "unwatched"])
    async def jellyfin_rec_new(self, ctx: commands.Context, jellyfinUsername: str):
        """
        Get a new movie, show or artist recommendation
        Include your jellyfin username
        """
        mediaType = None
        for group in jr.accepted_types:
            if group in ctx.message.content.lower():
                mediaType = group
                break
        if not mediaType:
            acceptedTypes = "', '".join(jr.accepted_types)
            await ctx.send("Please try again, indicating '{}'".format(acceptedTypes))
        else:
            holdMessage = await ctx.send("Looking for a new {}...".format(mediaType))
            async with ctx.typing():
                response, embed, mediaItem = jr.make_recommendation(mediaType=mediaType, unwatched=True,
                                                                    username=jellyfinUsername)
            await holdMessage.delete()
            if embed is not None:
                recMessage = await ctx.send(response, embed=embed)
            else:
                await ctx.send(response)
            if mediaItem and mediaItem.type not in ['artist', 'album', 'track']:
                await recMessage.add_reaction('🎞️')
                try:
                    def check(trailerReact, trailerReactUser):
                        return trailerReact.emoji == '🎞️' and trailerReactUser.id != self.bot.user.id

                    showTrailer, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                    if showTrailer:
                        await ctx.send(jr.get_trailer_URL(mediaItem=mediaItem))
                except asyncio.TimeoutError:
                    await recMessage.clear_reactions()

    @jellyfin_rec_new.error
    async def jellyfin_rec_new_error(self, ctx, error):
        print(error)
        await ctx.send("Sorry, something went wrong while looking for a new recommendation.")

    @jellyfin.command(name="current", aliases=["now"], hidden=True, pass_context=True)
    @has_admin_role
    async def jellyfin_now(self, ctx: commands.Context):
        """
        Current Jellyfin activity
        """
        global live_session_ids
        live_session_ids.clear()
        sessions = jf.getLiveSessions()
        if sessions:
            transcode_count = sum(1 for x in sessions if x.method == 'Transcode')
            overview_message = f"Sessions: {len(sessions)} {'stream' if len(sessions) == 1 else 'streams'} ({transcode_count} {'transcode' if transcode_count == 1 else 'transcodes'})"
            count = 0
            final_message = overview_message + "\n"
            for session in sessions:
                try:
                    count = count + 1
                    stream_message = f"**({count})** {selectIcon(str(session.state.lower()))} {session.username}: *{session.title}*\n" \
                                     f"__Player__: {session.client} ({session.deviceName})\n" \
                                     f"{'(Transcoding)' if session.method == 'Transcode' else ''}"
                    final_message += f"\n{stream_message}\n"
                    live_session_ids.append(session.deviceId)
                except ValueError:
                    live_session_ids.append("000")
                    pass
            sent_message = await ctx.send(final_message)
            """
            # feature currently unavailable, 500 error on Jellyfin when trying to change stream state
            if live_session_ids:
                await ctx.send(final_message + "\nTo terminate a stream, react with the stream number.")
                for i in range(count):
                    await sent_message.add_reaction(emoji_numbers[i])
                manage_streams = True
                while manage_streams:
                    def check(reaction, user):
                        return user != sent_message.author
                    try:
                        reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                        if reaction and str(reaction.emoji) in emoji_numbers:
                            try:
                                loc = emoji_numbers.index(str(reaction.emoji))
                                if jf.stopStream(stream_id=live_session_ids[loc],
                                                 message_to_viewer='The admin has stopped your stream.'):
                                    end_notification = await ctx.send(content=f"Stream {loc + 1} was ended.")
                                    await end_notification.delete(delay=1.0)
                            except Exception as e:
                                end_notification = await ctx.send(content="Something went wrong.")
                                await end_notification.delete(delay=1.0)
                    except asyncio.TimeoutError:
                        await sent_message.delete()
                        manage_streams = False
            """
        else:
            await ctx.send("No current activity.")


def setup(bot):
    bot.add_cog(Jellyfin(bot))
