"""
Interact with Yahoo Fantasy Sports
Copyright (C) 2020 Nathan Harris
"""

import discord
from discord.ext import commands, tasks
from discord.utils import get
from collections import defaultdict, OrderedDict
import random
import re
import json
import requests
# from progress.bar import Bar
import os
import datetime
from decimal import *
import math
import asyncio
from yahoo_oauth import OAuth2
import yahoo_fantasy_api as yfa
from urllib.parse import urlencode, quote, unquote
import base64
import hmac, hashlib
from requests_oauthlib import OAuth2Session

client_id = os.environ.get('FANTASY_BOT_ID')
client_secret = os.environ.get('FANTASY_BOT_SECRET')

access_token_url = 'https://api.login.yahoo.com/oauth2/get_token'

creds_folder = "yahoofantasy/credentials/"


def table_spaces(size, text):
    size = (size - len(text)) / 2
    space = ""
    for i in range(0, int(size)):
        space = space + " "
    space = space + text + space
    if len(space) > size:
        return " " + space[:-1] + " "
    else:
        return " " + space + " "


def league_check(league):
    """
    :param league:
    :return: league acronym or None
    """
    fixed = None
    if league in ['nfl', 'football']:
        fixed = 'nfl'
    if league in ['nhl', 'hockey']:
        fixed = 'nhl'
    if league in ['nba', 'basketball']:
        fixed = 'nba'
    if league in ['mlb', 'baseball']:
        fixed = 'mlb'
    if league in ['pnfl']:
        fixed = 'pnfl'
    if league in ['pmlb']:
        fixed = 'pmlb'
    return fixed


async def stat_check(league, stat, ctx):
    """
    :param league:
    :param stat:
    :return: Dict or False
    """
    for s in league.stat_categories():
        if stat == s['name'] or stat == s['display_name']:
            return s
    await ctx.send("Invalid statistic.")
    return None


async def check_auth(discordUser, ctx):
    if not os.path.exists(creds_folder + str(discordUser.id) + "_oauth2.json"):
        await ctx.send(
            "Sorry, I am not connected to your Yahoo Fantasy account. Please say the 'fantasy setup' command to "
            "link me to your account.")
        return False
    else:
        print("file exists")
        file = creds_folder + str(discordUser.id) + "_oauth2.json"
        print(file)
        oauth = OAuth2(None, None, from_file=file)
        if not oauth.token_is_valid():
            oauth.refresh_access_token()
        return oauth


async def get_league(league, year, ctx):
    """
    :param league: str
    :param year: int
    :param ctx: commands.Context
    :return: League
    """
    auth = await check_auth(ctx.message.author, ctx)
    league = league_check(league.lower())
    if auth and league:
        game = yfa.Game(auth, league)
        ids = game.league_ids(year=year)
        if ids:
            league_id = ids[-1]
            return game.to_league(league_id)
        else:
            await ctx.send("It seems you don't play Fantasy for the " + league.upper())
    elif auth:
        await ctx.send("That is an incorrect league.")
    return None


async def get_user_team(league, year, ctx):
    """
    :param league: str
    :param year: int
    :param ctx: commands.Context
    :return: Team
    """
    auth = await check_auth(ctx.message.author, ctx)
    l = await get_league(league, year, ctx)
    if auth and l:
        return l.to_team(l.team_key())
    return None


async def get_specific_team(league, year, team_name, ctx):
    """
    :param league: str
    :param year: int
    :param team_name: str
    :param ctx: commands.Context
    :return: Team
    """
    l = await get_league(league, year, ctx)
    if l:
        for t in l.teams():
            if t['name'].lower() == team_name.lower():
                return l.to_team(t['team_key'])
        await ctx.send("I could not find that team.")
    return None


async def get_all_teams(league, year, ctx):
    """
    :param league: str
    :param year: int
    :param ctx: commands.Context
    :return: {name: id, ...}
    """
    l = await get_league(league, year, ctx)
    if l:
        return l.teams()
    return None


class YahooFantasy(commands.Cog):
    """
    DM Channel work
    """

    async def interact(self, whatToSay, discordUser, needResponse=False):
        if discordUser.dm_channel is None:
            await discordUser.create_dm()
        await discordUser.dm_channel.send(whatToSay)
        if needResponse:
            def check(m):
                return m.content and m.channel == discordUser.dm_channel and m.author == discordUser

            try:
                msg = await self.bot.wait_for('message', timeout=120.0, check=check)
                return msg.content
            except asyncio.TimeoutError:
                await discordUser.dm_channel.send("Sorry, you took too long. Please start over by saying 'setup'")
                return False

    async def authenticate(self, discordUser):
        yahoo = OAuth2Session(client_id, redirect_uri='oob')
        auth_url = "https://api.login.yahoo.com/oauth2/request_auth?client_id=" + client_id + '&redirect_uri=oob' \
                                                                                              '&response_type=code&scope=openid&nonce=' + str(
            random.randint(0, 999999))

        auth_token = await self.interact(
            "Please visit this link to authorize access to your Yahoo Fantasy account:\n" + auth_url + "\n\nPaste the "
                                                                                                       "final code "
                                                                                                       "here:",
            discordUser, needResponse=True)

        if auth_token:
            auth_str = '%s:%s' % (client_id, client_secret)
            encoded = base64.b64encode(bytes(auth_str, 'utf-8'))

            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': 'Basic %s' % str(encoded)
            }

            res = yahoo.fetch_token(access_token_url, code=auth_token, client_id=client_id, client_secret=client_secret)

            file_contents = {
                'access_token': res['access_token'],
                'consumer_key': client_id,
                'consumer_secret': client_secret,
                'guid': res['xoauth_yahoo_guid'],
                'refresh_token': res['refresh_token'],
                'token_time': float(res['expires_at']) - float(res['expires_in']),
                'token_type': res['token_type']
            }

            f = open(creds_folder + str(discordUser.id) + '_oauth2.json', 'w+')
            f.write(json.dumps(file_contents))
            f.close()

            await self.interact(
                "I am now connected to your Yahoo Fantasy account. I will automatically use your account when "
                "providing answers.",
                discordUser, needResponse=False)

    """
    Regular channel work
    """

    @commands.group(aliases=["Fantasy"], pass_context=True)
    async def fantasy(self, ctx: commands.Context):
        """
        Yahoo Fantasy commands
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")

    @fantasy.command(name="setup", aliases=['start', 'connect'], pass_context=True)
    async def fantasy_setup(self, ctx: commands.Context):
        """
        Connect your Yahoo Fantasy account
        """
        await ctx.send("Please check your direct messages to connect me to your Yahoo Fantasy account.")
        await self.authenticate(ctx.author)

    @fantasy_setup.error
    async def fantasy_setup_error(self, ctx, error):
        await ctx.send("Sorry, something went wrong.")
        print(error)

    @fantasy.command(name="teams", pass_context=True)
    async def fantasy_teams(self, ctx: commands.Context, league: str, year: int = None):
        """
        List the teams in your league for a specific year
        Defaults to current year
        """
        teams = await get_all_teams(league, year, ctx)
        team_list = "```"
        for t in teams:
            team_list = team_list + t['name'] + "\n"
        team_list = team_list[:-1] + "```"
        await ctx.send(team_list)

    @fantasy_teams.error
    async def fantasy_teams_error(self, ctx, error):
        await ctx.send("Please include a valid <league>")

    @fantasy.command(name="compare", pass_context=True)
    async def fantasy_compare(self, ctx: commands.Context, league: str, player1: str, player2: str):
        """
        Compare two players' statistics
        Put the player's names in quotes
        """
        l = await get_league(league, None, ctx)
        if l:
            stat_categories = l.stat_categories()
            stat_name_ids = {}
            for s in stat_categories:
                stat_name_ids[s['name']] = str(s['stat_id'])
            try:
                p1 = l.player_details(player1)
            except:
                await ctx.send("I couldn't find that first player.")
            try:
                p2 = l.player_details(player2)
            except:
                await ctx.send("I couldn't find that second player.")
            if p1 and p2:
                p1_stats = {}
                p2_stats = {}
                for s in p1['player_stats']['stats']:
                    p1_stats[s['stat']['stat_id']] = s['stat']['value']
                for s in p2['player_stats']['stats']:
                    p2_stats[s['stat']['stat_id']] = s['stat']['value']
                length = 0
                for s, i in stat_name_ids.items():
                    if len(s) > length:
                        length = len(s)
                embed = discord.Embed(title=str(p1['name']['full']) + " vs. " + str(p2['name']['full']))
                count = 1
                for s, i in stat_name_ids.items():
                    if str(i) in p1_stats and str(i) in p2_stats:
                        embed.add_field(name=table_spaces(len(p1['name']['full']), p1_stats[i]) + "|" + table_spaces(
                            len(p2['name']['full']), p2_stats[i]), value=s, inline=False)
                        count = count + 1
                if count > 1:
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("No stats for those players.")
            elif p1:
                await ctx.send("I couldn't find that second player.")
            elif p2:
                await ctx.send("I couldn't find that first player.")
            else:
                await ctx.send("I couldn't find either of those players.")

    @fantasy_compare.error
    async def fantasy_compare_error(self, ctx, error):
        await ctx.send("Please include two players, each in \"\"")

    @fantasy.command(name="agents", aliases=["free"], pass_context=True)
    async def fantasy_free_agents(self, ctx: commands.Context, league: str, position: str, stat: str):
        """
        List the top free agents for a specific position
        """
        l = await get_league(league, None, ctx)
        if l:
            stat = await stat_check(l, stat, ctx)
            if stat:
                if position.upper() in l.positions():
                    fa = l.free_agents(position.upper())
                    print(fa)
                    await ctx.send(len(fa))
                    stat_id = stat['stat_id']
                    fa_stats = {}
                    for a in fa:
                        for s in l.player_details(a['name'])['player_stats']['stats']:
                            # print(s)
                            if s['stat']['stat_id'] == str(stat_id):
                                if s['stat']['value'] == "-":
                                    fa_stats[a['name']] = 0
                                else:
                                    fa_stats[a['name']] = int(s['stat']['value'])
                    fa_stats = OrderedDict(sorted(fa_stats.items(), key=lambda kv: (kv[1], kv[0]), reverse=True))
                    count = 1
                    embed = discord.Embed(title="Top " + position.upper() + " free agents, ranked by " + stat['name'])
                    for n, v in fa_stats.items():
                        if count < 24:
                            embed.add_field(name=n + " - " + str(v), value=(l.player_details(n)[
                                                                                'editorial_name_full_name'] if 'editorial_name_full_name' in n.keys() else '\u200b'))
                            count += 1
                    if count > 1:
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send("There are no free agents for " + position.upper())
                else:
                    positions_list = ""
                    for p in l.positions():
                        positions_list = positions_list + p + ", "
                    await ctx.send(
                        "That position doesn't exist. Please use the available positions: " + positions_list[:-2])

    @fantasy_free_agents.error
    async def fantasy_free_agents_error(self, ctx, error):
        await ctx.send("Sorry, something went wrong.")

    @fantasy.command(name="roster", pass_context=True)
    async def fantasy_roster(self, ctx: commands.Context, league: str, week: int = None):
        """
        Get your team roster for a specific week
        Defaults to current week
        """
        team = await get_user_team(league, None, ctx)
        if team:
            roster = team.roster(week=week)
            embed = discord.Embed(title="Roster for " + ("current week" if week is None else "Week " + str(week)))
            count = 1
            for p in roster:
                if count < 24:
                    embed.add_field(name=p['name'] + " - " + p['selected_position'],
                                    value=(p['status'] if p['status'] else '\u200b'))
                    count += 1
                else:
                    ctx.send(embed=embed)
                    embed = discord.Embed(
                        title="Roster for " + (
                            "current week" if week is None else "Week " + str(week)) + " (Page " + str(
                            count / 24) + ")")
            await ctx.send(embed=embed)

    @fantasy_roster.error
    async def fantasy_roster_error(self, ctx, error):
        await ctx.send("Sorry, something went wrong.")

    def __init__(self, bot):
        self.bot = bot
        print("YahooFantasy ready to go.")


def setup(bot):
    bot.add_cog(YahooFantasy(bot))
