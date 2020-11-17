"""
Parse RSS feeds for major online media outlets
Copyright (C) 2019 Nathan Harris
"""

from discord.ext import commands, tasks
import discord
import urllib
from urllib import request
import urllib.request
import re
from bs4 import BeautifulSoup
import requests
from collections import defaultdict
import json
import feedparser
import time
from datetime import datetime

feeds = {
    "brief":{
        "BBC":"http://feeds.bbci.co.uk/news/rss.xml",
        "CNN":"http://rss.cnn.com/rss/cnn_topstories.rss",
        "NPR":"https://www.npr.org/rss/rss.php?id=1001",
        "NYT":"https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        "Reut":"https://news.google.com/rss/search?q=when:24h+allinurl:reuters.com&ceid=US:en&hl=en-US&gl=US",
        "USAT":"http://rssfeeds.usatoday.com/usatoday-NewsTopStories",
        "WSJ":"https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml",
        "WP":"http://feeds.washingtonpost.com/rss/national"
    },
    "top":{
        "BBC":"http://feeds.bbci.co.uk/news/rss.xml",
        "CNN":"http://rss.cnn.com/rss/cnn_topstories.rss",
        "NYT":"https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        "Reut":"https://news.google.com/rss/search?q=when:24h+allinurl:reuters.com&ceid=US:en&hl=en-US&gl=US",
        "USAT":"http://rssfeeds.usatoday.com/usatoday-NewsTopStories"
    },
    "latest":{
       "CNN":"http://rss.cnn.com/rss/cnn_latest.rss",
       "NPR":"https://www.npr.org/rss/rss.php?id=1001",
       "NYT":"https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
       "USAT":"http://rssfeeds.usatoday.com/usatoday-NewsTopStories"
    },
    "world":{
        "BBC":"http://feeds.bbci.co.uk/news/world/rss.xml",
        "CNN":"http://rss.cnn.com/rss/cnn_world.rss",
        "NPR":"https://www.npr.org/rss/rss.php?id=1004",
        "NYT":"https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "Reut":"https://news.google.com/rss/search?q=when:24h+allinurl:reuters.com&ceid=US:en&hl=en-US&gl=US",
        "USAT":"http://rssfeeds.usatoday.com/UsatodaycomWorld-TopStories",
        "WSJ":"https://feeds.a.dj.com/rss/RSSWorldNews.xml",
        "WP":"http://feeds.washingtonpost.com/rss/world"
    },
    "us":{
        "CNN":"http://rss.cnn.com/rss/cnn_us.rss",
        "NPR":"https://www.npr.org/rss/rss.php?id=1003",
        "NYT":"https://rss.nytimes.com/services/xml/rss/nyt/US.xml",
        "USAT":"http://rssfeeds.usatoday.com/UsatodaycomNation-TopStories",
        "WSJ":"https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml",
        "WP":"http://feeds.washingtonpost.com/rss/national"
    },
    "sports":{
        "CNN":"http://rss.cnn.com/rss/edition_sport.rss",
        "ESPN":"https://www.espn.com/espn/rss/news",
        "NYT":"https://rss.nytimes.com/services/xml/rss/nyt/Sports.xml",
        "USAT":"http://rssfeeds.usatoday.com/UsatodaycomSports-TopStories",
        "WP":"http://feeds.washingtonpost.com/rss/sports"
    }
}
    
outlets={
    "BBC":"BBC",
    "CNN":"CNN",
    "ESPN":"ESPN",
    "NPR":"NPR",
    "NYT":"The New York Times",
    "Reut":"Reuters",
    "USAT":"USA Today",
    "WSJ":"The Wall Street Journal",
    "WP":"The Washington Post"
}

class News(commands.Cog):
    
    def get_single_headline(self, category, outlet):
        f = feedparser.parse(feeds[category][outlet])
        return f['entries'][0]['title'], f['entries'][0].link
    
    def get_headlines(self, category, outlet, number: int = 5):
        f = feedparser.parse(feeds[category][outlet])
        data = []
        for i in range(0, number):
            data.append(f['entries'][i])
        return data
    
    def get_outlet(self, data):
        if data.lower() in ['bbc','british broadcasting channel''bbc.com','cbbc']:
            return 'BBC'
        elif data.lower() in ['cnn','cable news network','cnn.com','fake news', 'fakenews']:
            return 'CNN'
        elif data.lower() in ['espn']:
            return 'ESPN'
        elif data.lower() in ['npr','national public radio','public radio','radio']:
            return "NPR"
        elif data.lower() in ['nyt','new york times','ny times','nytimes','times','the times','nyt.com','newyorktimes','nytimes.com']:
            return 'NYT'
        elif data.lower() in ['reuters','rutgers','rueters']:
            return 'Reut'
        elif data.lower() in ['usa','usat','usatoday','usa today','today','gannett']:
            return 'USAT'
        elif data.lower() in ['wsj','journal','wall street','wall street journal','ws jousnal']:
            return 'WSJ'
        elif data.lower() in ['wp','wapo','washington post','post','the post','washingtonpost','washingtonpost.com','wapo.com']:
            return 'WP'
        else:
            return None
        
    def unescape(self, s):
        s = s.replace("&lt;", "<")
        s = s.replace("&gt;", ">")
        s = s.replace("&apos;", "'")
        s = s.replace("&amp;", "&")
        return s

    def add_embed_field(self, embed, title, outlet_name, link):
        embed.add_field(name=self.unescape(title), value=f"[*{outlet_name}*]({link})", inline=False)
    
    def make_category_response_embed(self, embed_title: str, category: str, count: int = 5):
        embed = discord.Embed(title=embed_title)
        for o in feeds[category]:
            t, l = self.get_single_headline(category, o)
            self.add_embed_field(embed=embed, title=t, link=l, outlet_name=outlets[o])
        return embed

    @commands.group(pass_context=True, case_insensitive=True)
    async def news(self, ctx: commands.Context):
        """
        Get news headlines and links
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")
    
    @news.command(name="from", pass_context=True, case_insensitive=True)
    async def news_from(self, ctx: commands.Context, *, outlet: str):
        """
        Top headlines from a specific outlet
        """
        if outlet == 'all':
            return self.news_brief(ctx=ctx)
        o = self.get_outlet(outlet)
        if not o:
            await ctx.send(f"{outlet} is not supported.")
        else:
            embed = discord.Embed(title=f"Top News from {outlets[o]}")
            h = self.get_headlines("top", o, 5)
            for i in h:
                embed.add_field(name=self.unescape(i['title']),
                                value=f"[{str(time.strftime('%b %d, %Y, %I:%M %p', i.updated_parsed))}]({i['link']})",
                                inline=False)
            await ctx.send(embed=embed)
            
    @news_from.error
    async def news_top_error(self, ctx, error):
        await ctx.send("Something went wrong. Please try again with another outlet.")
        
    @news.command(name="outlets", pass_context=True, case_insensitive=True)
    async def news_outlets(self, ctx: commands.Context):
        """
        List all available outlets
        """
        await ctx.send(f"Available outlets: {', '.join(outlet for outlet in feeds['top'].keys())}")

    @news.command(name="brief", aliases=['all'], pass_context=True, case_insensitive=True)
    async def news_brief(self, ctx: commands.Context):
        """
        Top news headlines
        """
        embed = self.make_category_response_embed(embed_title="News Brief", category='brief', count=5)
        await ctx.send(embed=embed)

    @news_brief.error
    async def news_brief_error(self, ctx, error):
        await ctx.send("Something went wrong. Please try again later.")


    @news.command(name="world", aliases=["international"], pass_context=True, case_insensitive=True)
    async def news_world(self, ctx: commands.Context):
        """
        World news headlines
        """
        embed = self.make_category_response_embed(embed_title="World News", category='world')
        await ctx.send(embed=embed)
        
    @news_world.error
    async def news_world_error(self, ctx, error):
        await ctx.send("Something went wrong. Please try again later.")
        
    @news.command(name="u.s", aliases=["us", "america", "united states", "national"], pass_context=True, case_insensitive=True)
    async def news_us(self, ctx: commands.Context):
        """
        U.S. news headlines
        """
        embed = self.make_category_response_embed(embed_title="U.S. News", category='us')
        await ctx.send(embed=embed)
        
    @news_us.error
    async def news_us_error(self, ctx, error):
        await ctx.send("Something went wrong. Please try again later.")
        
    @news.command(name="sports", aliases=["sport"], pass_context=True, case_insensitive=True)
    async def news_sports(self, ctx: commands.Context):
        """
        Sports news headlines
        """
        embed = self.make_category_response_embed(embed_title="Sports News", category='sports')
        await ctx.send(embed=embed)
        
    @news_sports.error
    async def news_sports_error(self, ctx, error):
        await ctx.send("Something went wrong. Please try again later.")
    
    def __init__(self, bot):
        self.bot = bot
        print("News ready.")


def setup(bot):
    bot.add_cog(News(bot))