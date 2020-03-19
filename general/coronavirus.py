"""
Get coronavirus data
Copyright (C) 2019 Nathan Harris
"""
import discord
from discord.ext import commands, tasks
import requests
from datetime import datetime


def get_data():
    json = requests.get('https://services1.arcgis.com/0MSEUqKaxRlEPj5g/arcgis/rest/services/ncov_cases/FeatureServer'
                        '/2/query?f=json&where=1%3D1&returnGeometry=false&spatialRel=esriSpatialRelIntersects'
                        '&outFields=*&orderByFields=Confirmed%20desc&resultOffset=0&resultRecordCount=250&cacheHint'
                        '=true').json()
    return [country['attributes'] for country in json['features']]


def convert_to_length(text, length):
    text = str(text)
    print(text)
    print(len(text))
    if length > len(text):
        text = text.rjust(length - len(text))
        print(text)
    return text


def make_list(data):
    timestamp = int(str(data[0]['Last_Update'])[:-3])
    timestamp = datetime.fromtimestamp(timestamp).strftime('%B %d, %Y %H:%M')
    response = "Conavirus numbers (Updated {})\n\n".format(timestamp)
    response += "%40s|%10s|%7s|%10s\n\n" % ("Country", "Confirmed", "Death", "Recovered")
    for country in data:
        response += "%40s|%10s|%7s|%10s\n" % (
        country['Country_Region'], str(country['Confirmed']), str(country['Deaths']), str(country['Recovered']))
    return response


class Coronavirus(commands.Cog):

    @commands.command(name="coronavirus", aliases=['corona'], pass_content=True)
    async def coronavirus(self, ctx: commands.Context):
        """
        Get global data on the coronavirus (via ArcGIS)
        """
        data = get_data()
        if data:
            list = make_list(data)
            temp_list = ""
            for line in list.splitlines():
                if len(temp_list) < 1800:
                    temp_list += "\n" + line
                else:
                    await ctx.send("```" + temp_list + "```")
                    temp_list = ""
            await ctx.send("```" + temp_list + "```")
        else:
            await ctx.send("Sorry, I couldn't grab the latest numbers")

    @coronavirus.error
    async def coronavirus_error(self, ctx, error):
        print(error)
        await ctx.send("Something went wrong.")

    def __init__(self, bot):
        self.bot = bot
        print("Coronavirus ready to go!")


def setup(bot):
    bot.add_cog(Coronavirus(bot))
