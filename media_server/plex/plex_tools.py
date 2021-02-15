"""
Parse Plex Media Server statistics via Tautulli's API
Copyright (C) 2019 Nathan Harris
"""
from collections import defaultdict

from discord.ext import commands

import helper.discord_helper as discord_helper
from helper.decorators import has_admin_role

from media_server import multi_server_handler

shows = defaultdict(list)
movies = defaultdict(list)


class PlexTools(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        print("Plex Tools - updating libraries...")
        # self.makeLibraries.start()

    """
    @tasks.loop(minutes=60.0)  # update library every hour
    async def makeLibraries(self):
        pr.cleanLibraries()
        for groupName in pr.libraries.keys():
            pr.makeLibrary(groupName)
        print("Libraries updated.")
        print("Plex ready.")
    """

    @commands.group(name="plex", aliases=["Plex"], pass_context=True)
    async def plex(self, ctx: commands.Context):
        """
        Plex Media Server commands
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")

    @plex.command(name="switch", aliases=["default"], pass_context=True)
    async def plex_switch(self, ctx: commands.Context, server_number: int):
        """
        Change current/default Plex Media Server
        """
        plex_api = multi_server_handler.get_plex_api(ctx=ctx)
        plex_api.database.update_default_server_number(media_server_type="plex", server_number=server_number)
        await ctx.send(f"Now using Plex Server #{server_number}")

    @plex_switch.error
    async def plex_switch_error(self, ctx, error):
        print(error)
        await discord_helper.something_went_wrong(ctx=ctx)

    """
    @plex.command(name="update", aliases=["refresh"], pass_context=True)
    async def plex_update(self, ctx: commands.Context):
        # Update Plex libraries for Plex Recs
        message = await ctx.send("Updating Plex libraries...")
        pr.cleanLibraries()
        for groupName in pr.libraries.keys():
            pr.makeLibrary(groupName)
        await message.edit(content="Plex libraries updated.")
        
    """

    @plex.command(name="stats", aliases=["statistics"], pass_context=True)
    async def plex_stats(self, ctx: commands.Context, plex_username: str):
        """
        Watch time statistics for a user
        """
        user_id = None
        for user in current_plex_instance.tautulli.get_user_names(remove_response=True):
            if user['friendly_name'] == plex_username:
                user_id = user['user_id']
                break
        if not user_id:
            await ctx.send("User not found.")
        else:
            embed = discord.Embed(title=f"{plex_username}'s Total Plex Watch Time")
            for user in current_plex_instance.tautulli.get_user_watch_time_stats(user_id=user_id, remove_response=True):
                embed.add_field(name=f"{datetime.timedelta(seconds=int(user['total_time']))}, {user['total_plays']} plays",
                                value=f"Last {user['query_days']} Day{('s' if int(user['query_days']) > 1 else '')}"
                                if int(user['query_days']) != 0
                                else "All Time ",
                                inline=False)
            await ctx.send(embed=embed)

    @plex_stats.error
    async def plex_stats_error(self, ctx, error):
        await ctx.send("Please include a Plex username")

    @plex.command(name="size", aliases=["library"], pass_context=True)
    async def plex_size(self, ctx: commands.Context):
        """
        Size of Plex libraries
        """
        embed = discord.Embed(title=f"{current_plex_instance.name} Library Statistics")
        size = 0
        for lib in current_plex_instance.tautulli.get_libraries(remove_response=True):
            if lib['section_name'] not in ['']:  # Exempt sections from list if needed
                size += current_plex_instance.tautulli.get_library_media_info(section_id=lib['section_id'], remove_response=True).get('total_file_size', 0)
                if lib['section_type'] == 'movie':
                    embed.add_field(name=str(lib['count']) + " movies", value=str(lib['section_name']), inline=False)
                elif lib['section_type'] == 'show':
                    embed.add_field(name=str(lib['count']) + " shows, " + str(lib['parent_count']) + " seasons, " + str(
                        lib['child_count']) + " episodes", value=str(lib['section_name']), inline=False)
                elif lib['section_type'] == 'artist':
                    embed.add_field(name=str(lib['count']) + " artists, " + str(lib['parent_count']) + " albums, " + str(
                        lib['child_count']) + " songs", value=str(lib['section_name']), inline=False)
        embed.add_field(name='\u200b', value="Total: " + filesize(size))
        await ctx.send(embed=embed)

    @plex.command(name="top", aliases=["pop"], pass_context=True)
    async def plex_top(self, ctx: commands.Context, searchTerm: str, timeRange: int):
        """
        Most popular media or most active users during time range (in days)
        Use 'movies','shows','artists' or 'users'
        """
        stats = current_plex_instance.tautulli.home_stats(time_range=timeRange,
                                                          stat_category=searchTerm.lower(),
                                                          stat_type='duration',
                                                          stat_count=5)
        if not stats:
            await ctx.send("Please try again. Use 'movies','shows','artists' or 'users'")
        else:
            count = 1
            if searchTerm.lower() == "users":
                embed = discord.Embed(title=f"Most active users in past f{timeRange} day{('s' if timeRange > 1 else '')}")
                for user in stats:
                    embed.add_field(name=f"{count}. {user['friendly_name']}",
                                    value=f"{user['total_plays']} play{('s' if int(user['total_plays']) > 1 else '')}",
                                    inline=False)
            else:
                embed = discord.Embed(
                    title=f"Most popular {searchTerm.lower()} in past f{timeRange} day{('s' if timeRange > 1 else '')}")
                for entry in stats:
                    embed.add_field(name=f"{count}. {entry['title']}",
                                    value=f"{entry['total_plays']} play{('s' if int(entry['total_plays']) > 1 else '')}",
                                    inline=False)
                    count = count + 1
            await ctx.send(embed=embed)

    @plex_top.error
    async def plex_top_error(self, ctx, error):
        await ctx.send("Please include <movies|shows|artists|users> <timeFrame>")

    @plex.command(name="current", aliases=["now"], hidden=True, pass_context=True)
    @has_admin_role
    async def plex_now(self, ctx: commands.Context):
        """
        Current Plex activity
        """
        json_data = current_plex_instance.tautulli.current_activity(remove_response=True)
        try:
            stream_count = json_data['stream_count']
            transcode_count = json_data['stream_count_transcode']
            total_bandwidth = json_data['total_bandwidth']
            lan_bandwidth = json_data['lan_bandwidth']
            overview_message = tautulli.build_overview_message(stream_count=stream_count,
                                                               transcode_count=transcode_count,
                                                               total_bandwidth=total_bandwidth,
                                                               lan_bandwidth=lan_bandwidth)
            sessions = json_data['sessions']
            count = 0
            final_message = overview_message + "\n"
            for session in sessions:
                try:
                    count += 1
                    stream_message = tautulli.build_stream_message(session_data=session,
                                                                   count=count,
                                                                   state=session['state'],
                                                                   username=session['username'],
                                                                   title=session['full_title'],
                                                                   player=session['player'],
                                                                   product=session['product'],
                                                                   quality_profile=session['quality_profile'],
                                                                   stream_container_decision=session['stream_container_decision'],
                                                                   bandwidth=session['bandwidth'],
                                                                   auto_decode=True)
                    final_message = final_message + "\n" + stream_message + "\n"
                    session_ids.append(str(session['session_id']))
                except ValueError:
                    session_ids.append("000")
                    pass
            if int(stream_count) > 0:
                sent_message = await ctx.send(final_message + "\nTo terminate a stream, react with the stream number.")
                await discord_styling.add_emoji_number_reactions(message=sent_message, count=count)

                manage_streams = True
                while manage_streams:
                    def check(reaction, user):
                        return user != sent_message.author and str(reaction.emoji) in discord_styling.emoji_numbers

                    try:
                        reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                        if reaction and str(reaction.emoji) in discord_styling.emoji_numbers:
                            try:
                                loc = discord_styling.emoji_numbers.index(str(reaction.emoji))
                                if current_plex_instance.tautulli.terminate_session(session_id=session_ids[loc],
                                                                                    message=settings.TERMINATE_MESSAGE):
                                    end_notification = await ctx.send(content=f"Stream {loc + 1} was ended.")
                                else:
                                    end_notification = await ctx.send(content=f"Could not stop stream {loc + 1}")
                                await end_notification.delete(delay=1.0)
                            except:
                                end_notification = await ctx.send(content="Something went wrong.")
                                await end_notification.delete(delay=1.0)
                    except asyncio.TimeoutError:
                        await sent_message.delete()
                        manage_streams = False
            else:
                await ctx.send("No current activity.")
        except KeyError:
            await ctx.send(discord_styling.bold("Connection error."))

    @plex.command(name="new", alias=["added"], pass_context=True)
    async def plex_new(self, ctx: commands.Context):
        """
        See recently added content
        """
        e = discord.Embed(title=f"Recently Added to {current_plex_instance.name}")
        count = 5
        cur = 0
        recently_added = current_plex_instance.tautulli.recently_added(count=count, remove_response=True)
        new_items = []
        for i in range(0, count):
            listing = recently_added['recently_added'][i]
            item = {
                'url': current_plex_instance.tautulli.image_thumb_url(thumb=listing['thumb']),
                'description': "({loc}/{count}) {title} - [Watch Now]({link})".format(
                    loc=str(i + 1),
                    count=str(count),
                    title=(listing['grandparent_title']
                           if listing['grandparent_title']
                           else (listing['parent_title']
                                 if listing['parent_title']
                                 else listing['full_title'])
                           ),
                    link=current_plex_instance.get_watch_now_link(rating_key=listing['rating_key'])
                ),
            }
            new_items.append(item)
        e.set_image(url=new_items[cur]['url'])
        e.description = new_items[cur]['description']
        ra_embed = await ctx.send(embed=e)
        nav = True
        while nav:
            def check(reaction, user):
                return user != ra_embed.author and str(reaction.emoji) in [u"\u27A1", u"\u2B05"]

            try:
                if cur == 0:
                    await ra_embed.add_reaction(u"\u27A1")  # arrow_right
                elif cur == count - 1:
                    await ra_embed.add_reaction(u"\u2B05")  # arrow_left
                else:
                    await ra_embed.add_reaction(u"\u2B05")  # arrow_left
                    await ra_embed.add_reaction(u"\u27A1")  # arrow_right
                reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
            except asyncio.TimeoutError:
                await ra_embed.delete()
                nav = False
                current_plex_instance.tautulli.delete_image_cache()
            else:
                if reaction.emoji == u"\u27A1":
                    if cur + 1 < count:
                        cur += 1
                        e.set_image(url=new_items[cur]['url'])
                        e.description = new_items[cur]['description']
                        await ra_embed.edit(embed=e)
                        await ra_embed.clear_reactions()
                else:
                    if cur - 1 >= 0:
                        cur -= 1
                        e.set_image(url=new_items[cur]['url'])
                        e.description = new_items[cur]['description']
                        await ra_embed.edit(embed=e)
                        await ra_embed.clear_reactions()

    @plex.command(name="search", alias=["find"], pass_context=True)
    async def plex_search(self, ctx: commands.Context, *, searchTerm: str):
        """
        Search for Plex content
        """
        json_data = current_plex_instance.tautulli.search(keyword=searchTerm)
        embed = discord.Embed(title=f"'{searchTerm}' Search Results")
        if json_data['results_count'] > 0:
            for k, l in json_data['results_list'].items():
                results = ""
                results_list = []
                if k.lower() not in ['episode']:  # ignore episode titles
                    for r in l:
                        if searchTerm.lower() in str(r['title']).lower():
                            if r['title'] in results_list or k == 'collection':
                                results_list.append(r['title'] + " - " + r['library_name'])
                                results += "[{title} - {lib}]({link})\n".format(
                                    title=r['title'],
                                    lib=r['library_name'],
                                    link=current_plex_instance.get_watch_now_link(rating_key=r['rating_key'])
                                )
                            else:
                                results_list.append(r['title'])
                                results += "[{title}]({link})\n".format(
                                    title=r['title'],
                                    link=current_plex_instance.get_watch_now_link(rating_key=r['rating_key'])
                                )
                    if results:
                        embed.add_field(name=k.capitalize() + ("s" if len(results_list) > 1 else ""),
                                        value=str(results), inline=False)
        await ctx.send(embed=embed)

    @plex_search.error
    async def plex_search_error(self, ctx, error):
        print(error)
        await ctx.send("Please include a search term.")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if reaction.emoji == '✅':
            username = db.find_user_in_db(ServerOrDiscord='Plex', data=user.id)[0]
            if username:
                url = current_plex_instance.url_in_message(message=reaction.message)
                if url:
                    rating_key = current_plex_instance.get_rating_key(url)
                    library_id, title = current_plex_instance.get_media_info(rating_key=rating_key)
                    media_item = current_plex_instance.get_media_item(title=title, rating_key=rating_key, library_id=library_id)
                    if media_item:
                        playlist_title = settings.SUBSCRIBER_PLAYLIST_TITLE.format(username) \
                            if media_item.type in ['artist', 'album', 'track'] \
                            else settings.SUBSCRIBER_WATCHLIST_TITLE.format(username)
                        try:
                            response = current_plex_instance.add_to_playlist(playlist_title=playlist_title,
                                                                             rating_key=rating_key,
                                                                             item_to_add=media_item)
                            reaction.message.channel.send(response)
                        except Exception as e:
                            print(e)
                            await reaction.message.channel.send(
                                "Sorry, something went wrong when trying to add this item to your playlist.")
                    else:
                        await reaction.message.channel.send("Sorry, I can't find that item.")


def setup(bot):
    bot.add_cog(PlexTools(bot))
