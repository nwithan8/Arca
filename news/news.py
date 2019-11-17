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
        "Reut":"http://feeds.reuters.com/reuters/topNews",
        "USAT":"http://rssfeeds.usatoday.com/usatoday-NewsTopStories",
        "WSJ":"https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml",
        "WP":"http://feeds.washingtonpost.com/rss/national"
    },
    "top":{
        "BBC":"http://feeds.bbci.co.uk/news/rss.xml",
        "CNN":"http://rss.cnn.com/rss/cnn_topstories.rss",
        "NYT":"https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        "Reut":"http://feeds.reuters.com/reuters/topNews",
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
        "Reut":"http://feeds.reuters.com/Reuters/worldNews",
        "USAT":"http://rssfeeds.usatoday.com/UsatodaycomWorld-TopStories",
        "WSJ":"https://feeds.a.dj.com/rss/RSSWorldNews.xml",
        "WP":"http://feeds.washingtonpost.com/rss/world"
    },
    "us":{
        "CNN":"http://rss.cnn.com/rss/cnn_us.rss",
        "NPR":"https://www.npr.org/rss/rss.php?id=1003",
        "NYT":"https://rss.nytimes.com/services/xml/rss/nyt/US.xml",
        "Reut":"http://feeds.reuters.com/Reuters/domesticNews",
        "USAT":"http://rssfeeds.usatoday.com/UsatodaycomNation-TopStories",
        "WSJ":"https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml",
        "WP":"http://feeds.washingtonpost.com/rss/national"
    },
    "sports":{
        "CNN":"http://rss.cnn.com/rss/edition_sport.rss",
        "ESPN":"https://www.espn.com/espn/rss/news",
        "NYT":"https://rss.nytimes.com/services/xml/rss/nyt/Sports.xml",
        "Reut":"http://feeds.reuters.com/reuters/sportsNews",
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
    
    def headline(self, category, outlet):
        f = feedparser.parse(feeds[category][outlet])
        return f['entries'][0]['title'], f['entries'][0].link
    
    def headlines(self, category, outlet, number):
        f = feedparser.parse(feeds[category][outlet])
        count = 0
        data = []
        for i in range(0,number):
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
    
    @commands.group(pass_context=True, case_insensitive=True)
    async def news(self, ctx: commands.Context):
        """
        Get news headlines and links
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")   
            
    @news.command(name="brief", pass_context=True, case_insensitive=True)
    async def news_brief(self, ctx: commands.Context):
        """
        Get 5 top headlines
        """
        embed = discord.Embed(title="News Brief")
        for o in feeds['brief']:
            t,l = self.headline("brief",o)
            embed.add_field(name=self.unescape(t),value="["+"*"+outlets[o]+"*"+"]("+l+")", inline=False)
            #embed.add_field(name="*"+outlets[o]+"*",value="["+self.unescape(t)+"]("+l+")", inline=False)
        await ctx.send(embed=embed)
    
    @news_brief.error
    async def news_brief_error(self, ctx, error):
        await ctx.send("Something went wrong. Please try again later.")
    
    @news.command(name="top", pass_context=True, case_insensitive=True)
    async def news_top(self, ctx: commands.Context, *, outlet: str):
        """
        Top headlines from a specific outlet
        Supported outlets: BBC, CNN, NYT, Reuters, USA Today
        """
        o = self.get_outlet(outlet)
        if o == None:
            await ctx.send("That outlet is not supported.")
        else:
            embed = discord.Embed(title="Top News from "+outlets[o])
            h = self.headlines("top",o,5)
            for i in h:
                embed.add_field(name=self.unescape(i['title']),value="["+str(time.strftime('%b %d, %Y, %I:%M %p',i.updated_parsed))+"]("+i['link']+")", inline=False)
                #embed.add_field(name=str(time.strftime('%b %d, %Y, %I:%M %p',i.updated_parsed)),value="["+self.unescape(i['title'])+"]("+i['link']+")", inline=False)
            await ctx.send(embed=embed)
            
    @news_top.error
    async def news_top_error(self, ctx, error):
        await ctx.send("Something went wrong. Please try again with another outlet.")
        
    @news.command(name="world",aliases=["international"], pass_context=True, case_insensitive=True)
    async def news_world(self, ctx: commands.Context):
        """
        World news headlines
        """
        embed = discord.Embed(title="World News")
        for o in feeds['world']:
            t,l = self.headline("world",o)
            embed.add_field(name=self.unescape(t),value="["+"*"+outlets[o]+"*"+"]("+l+")", inline=False)
            #embed.add_field(name="*"+outlets[o]+"*",value="["+self.unescape(t)+"]("+l+")", inline=False)
        await ctx.send(embed=embed)
        
    @news_world.error
    async def news_world_error(self, ctx, error):
        await ctx.send("Something went wrong. Please try again later.")
        
    @news.command(name="u.s",aliases=["us","america","united states","national"], pass_context=True, case_insensitive=True)
    async def news_us(self, ctx: commands.Context):
        """
        U.S. news headlines
        """
        embed = discord.Embed(title="U.S. News")
        for o in feeds['us']:
            t,l = self.headline("us",o)
            embed.add_field(name=self.unescape(t),value="["+"*"+outlets[o]+"*"+"]("+l+")", inline=False)
            #embed.add_field(name="*"+outlets[o]+"*",value="["+self.unescape(t)+"]("+l+")", inline=False)
        await ctx.send(embed=embed)
        
    @news_us.error
    async def news_us_error(self, ctx, error):
        await ctx.send("Something went wrong. Please try again later.")
        
    @news.command(name="sports",aliases=["sport"], pass_context=True, case_insensitive=True)
    async def news_sports(self, ctx: commands.Context):
        """
        Sports headlines
        """
        embed = discord.Embed(title="Sports News")
        for o in feeds['sports']:
            t,l = self.headline("sports",o)
            embed.add_field(name=self.unescape(t),value="["+"*"+outlets[o]+"*"+"]("+l+")", inline=False)
            #embed.add_field(name="*"+outlets[o]+"*",value="["+self.unescape(t)+"]("+l+")", inline=False)
        await ctx.send(embed=embed)
        
    @news_sports.error
    async def news_sports_error(self, ctx, error):
        await ctx.send("Something went wrong. Please try again later.")
    
    def __init__(self, bot):
        self.bot = bot
        print("News ready.")
