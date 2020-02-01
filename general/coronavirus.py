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
    response += "%20s|%10s|%7s|%10s\n\n" % ("Country", "Confirmed", "Death", "Recovered")
    for country in data:
        response += "%20s|%10s|%7s|%10s\n" % (
        country['Country_Region'], str(country['Confirmed']), str(country['Deaths']), str(country['Recovered']))
    return "```" + response + "```"
    """
    embed.add_field(name='\u200b', value="%20s|%10s|%7s|%10s" % (convert_to_length("Country", 20), convert_to_length("Confirmed", 10), convert_to_length("Deaths", 7), convert_to_length("Recovered", 10)),
                    inline=False)
    fc = 1
    for country in data:
        if fc > 25:
            embeds.append(embed)
            embed = discord.Embed()
            fc = 0
        print("%s|%s|%s|%s" % (
            convert_to_length(country['Country_Region'], 20), convert_to_length(str(country['Confirmed']), 10), convert_to_length(str(country['Deaths']), 7), convert_to_length(str(country['Recovered']), 10)))
        embed.add_field(name='\u200b', value="%20s|%10s|%7s|%10s" % (
            convert_to_length(country['Country_Region'], 20), convert_to_length(str(country['Confirmed']), 10), convert_to_length(str(country['Deaths']), 7), convert_to_length(str(country['Recovered']), 10)),
                        inline=False)
        fc += 1
    embeds.append(embed)
    return embeds
    """


class Coronavirus(commands.Cog):

    @commands.command(name="coronavirus", aliases=['corona'], pass_content=True)
    async def coronavirus(self, ctx: commands.Context):
        """
        Get global data on the coronavirus (via ArcGIS)
        """
        data = get_data()
        if data:
            await ctx.send(make_list(data))
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
