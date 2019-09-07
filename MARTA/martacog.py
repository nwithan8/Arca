import discord
from discord.ext import commands, tasks
from discord.utils import get
from collections import defaultdict
from marta.api import get_buses, get_trains
import re
import json
import requests
#from progress.bar import Bar
import os
import datetime
from decimal import *
import math
import asyncio

stations = {
    "AIRPORT STATION": [
    [
        'airport',
        'hartsfield',
        'hartsfield-jackson'
    ],
    "6000 S Terminal Pkwy Atlanta, GA 30337",
    "https://itsmarta.com/Airport.aspx"
    ],
    "ARTS CENTER STATION": [
    [
        'arts center'
    ],
    "1255 West Peachtree St Atlanta, GA 30309",
    "https://itsmarta.com/Arts-Center.aspx"
    ],
    "ASHBY STATION": [
    [
        'ashby'
    ],
    "65 Joseph E Lowery Blvd Atlanta, GA 30314",
    "https://itsmarta.com/Ashby.aspx"
    ],
    "AVONDALE STATION": [
    [
        'avondale'
    ],
    "915 E Ponce de Leon Ave Decatur, GA 30030",
    "https://itsmarta.com/Avondale.aspx"
    ],
    "BANKHEAD STATION": [
    [
        'bankhead'
    ],
    "1335 Donald Hollowell Pkwy Atlanta, GA 30318",
    "https://itsmarta.com/Bankhead.aspx"
    ],
    "BROOKHAVEN STATION": [
    [
        'brookhaven'
    ],
    "4047 Peachtree Road, NE Atlanta, GA 30319",
    "https://itsmarta.com/Brookhaven.aspx"
    ],
    "BUCKHEAD STATION": [
    [
        'buckhead'
    ],
    "3360 Peachtree Rd, NE Atlanta, GA 30326",
    "https://itsmarta.com/Buckhead.aspx"
    ],
    "CHAMBLEE STATION": [
    [
        'chamblee'
    ],
    "5200 New Peachtree Road Chamblee, GA 30341",
    "https://itsmarta.com/Chamblee.aspx"
    ],
    "CIVIC CENTER STATION": [
    [
        'civic center'
    ],
    "435 West Peachtree St, NW Atlanta, GA 30308",
    "https://itsmarta.com/Civic-Center.aspx"
    ],
    "COLLEGE PARK STATION": [
    [
        'college park'
    ],
    "3800 Main St Atlanta, GA 30337",
    "https://itsmarta.com/College-Park.aspx"
    ],
    "DECATUR STATION": [
    [
        'decatur'
    ],
    "400 Church St Decatur, GA 30030",
    "https://itsmarta.com/Decatur.aspx"
    ],
    "OMNI DOME STATION": [
    [
        'omni dome',
        'dome',
        'mercedes benz',
        'mercedes-benz',
        'cnn',
        'state farm arena',
        'philips arena',
        'gwcc',
        'georgia world congress center',
        'world congress center'
    ],
    "100 Centennial Olympic Park Atlanta, GA 30303",
    "https://itsmarta.com/Omni.aspx"
    ],
    "DORAVILLE STATION": [
    [
        'doraville'
    ],
    "6000 New Peachtree Rd Doraville, GA 30340",
    "https://itsmarta.com/Doraville.aspx"
    ],
    "DUNWOODY STATION": [
    [
        'dunwoody'
    ],
    "1118 Hammond Dr Atlanta, GA 30328",
    "https://itsmarta.com/Dunwoody.aspx"
    ],
    "EAST LAKE STATION": [
    [
        'east lake'
    ],
    "2260 College Ave Atlanta, GA 30307",
    "https://itsmarta.com/East-Lake.aspx"
    ],
    "EAST POINT STATION": [
    [
        'east point'
    ],
    "2848 East Main St East Point, GA 30344",
    "https://itsmarta.com/East-Point.aspx"
    ],
    "EDGEWOOD CANDLER PARK STATION": [
    [
        'edgewood',
        'candler park'
    ],
    "1475 DeKalb Ave, NE Atlanta, GA 30307",
    "https://itsmarta.com/Edgewood-Candler-Park.aspx"
    ],
    "FIVE POINTS STATION": [
    [
        'five points',
        '5 points',
        '5points'
    ],
    "30 Alabama St SW Atlanta, GA 30303",
    "https://itsmarta.com/Five-Points.aspx"
    ],
    "GARNETT STATION": [
    [
        'garnett'
    ],
    "225 Peachtree St, SW Atlanta, GA 30303",
    "https://itsmarta.com/Garnett.aspx"
    ],
    "GEORGIA STATE STATION": [
    [
        'georgia state',
        'gsu',
        'school'
    ],
    "170 Piedmont Ave, SE Atlanta, GA 30303",
    "https://itsmarta.com/Georgia-State.aspx"
    ],
    "HAMILTON E HOLMES STATION": [
    [
        'hamilton e holmes',
        'h.e. holmes',
        'he holmes'
    ],
    "70 Hamilton E Holmes Dr, NW Atlanta, GA 30311",
    "https://itsmarta.com/Hamilton-E-Holmes.aspx"
    ],
    "INDIAN CREEK STATION": [
    [
        'indian creek'
    ],
    "901 Durham Park Rd Stone Mountain, GA 30083",
    "https://itsmarta.com/Indian-Creek.aspx"
    ],
    "INMAN PARK STATION": [
    [
        'inman',
        'inman park'
    ],
    "055 DeKalb Ave, NE Atlanta, GA 30307",
    "https://itsmarta.com/Inman-Park.aspx"
    ],
    "KENSINGTON STATION": [
    [
        'kensington'
    ],
    "3350 Kensington Rd Decatur, GA 30032",
    "https://itsmarta.com/Kensington.aspx"
    ],
    "KING MEMORIAL STATION": [
    [
        'king memorial',
        'mlk'
    ],
    "377 Decatur St, SE Atlanta, GA 30312",
    "https://itsmarta.com/King-Memorial.aspx"
    ],
    "LAKEWOOD STATION": [
    [
        'lakewood'
    ],
    "2020 Lee St, SW Atlanta, GA 30310",
    "https://itsmarta.com/Lakewood.aspx"
    ],
    "LENOX STATION": [
    [
        'lenox'
    ],
    "955 East Paces Ferry Rd, NE Atlanta, GA 30326",
    "https://itsmarta.com/Lenox.aspx"
    ],
    "LINDBERGH STATION": [
    [
        'lindbergh'
    ],
    "2424 Piedmont Rd, NE Atlanta, GA 30324",
    "https://itsmarta.com/Lindbergh.aspx"
    ],
    "MEDICAL CENTER STATION": [
    [
        'medical center'
    ],
    "5711 Peachtree-Dunwoody Rd, NE Atlanta, GA 30342",
    "https://itsmarta.com/Medical-Center.aspx"
    ],
    "MIDTOWN STATION": [
    [
        'midtown'
    ],
    "41 Tenth St, NE Atlanta, GA 30309",
    "https://itsmarta.com/Midtown.aspx"
    ],
    "NORTH AVE STATION": [
    [
        'north ave',
        'north avenue',
        'gt',
        'georgia tech',
        'tech'
    ],
    "713 West Peachtree St, NW Atlanta, GA 30308",
    "https://itsmarta.com/North-Ave.aspx"
    ],
    "NORTH SPRINGS STATION": [
    [
        'north springs'
    ],
    "7010 Peachtree Dunwoody Rd Sandy Springs, GA 30328",
    "https://itsmarta.com/North-Springs.aspx"
    ],
    "OAKLAND CITY STATION": [
    [
        'oakland',
        'oakland city'
    ],
    "1400 Lee St, SW Atlanta, GA 30310",
    "https://itsmarta.com/Oakland-City.aspx"
    ],
    "PEACHTREE CENTER STATION": [
    [
        'peachtree center'
    ],
    "216 Peachtree St, NE Atlanta, GA 30303",
    "https://itsmarta.com/Peachtree-Center.aspx"
    ],
    "SANDY SPRINGS STATION": [
    [
        'sandy springs'
    ],
    "1101 Mount Vernon Hwy Atlanta, GA 30338",
    "https://itsmarta.com/Sandy-Springs.aspx"
    ],
    "VINE CITY STATION": [
    [
        'vine city'
    ],
    "502 Rhodes St, NW Atlanta, GA 30314",
    "https://itsmarta.com/Vine-City.aspx"
    ],
    "WEST END STATION": [
    [
        'west end'
    ],
    "680 Lee St, SW Atlanta, GA 30310",
    "https://itsmarta.com/West-End.aspx"
    ],
    "WEST LAKE STATION": [
    [
        'west lake'
    ],
    "80 Anderson Ave, SW Atlanta, GA 30314",
    "https://itsmarta.com/West-Lake.aspx"
    ]
}
    
class MARTA(commands.Cog):
            
    @commands.command(aliases=["MARTA"], pass_context=True)
    async def marta(self, ctx: commands.Context, station: str=None, line: str=None, direction: str=None):
        """
        MARTA commands
        """
        found=False
        stationName = "GEORGIA STATE STATION"
        if station != None: # Default to Georgia State Station if not specified
            stationName = str(station)
        for s in stations:
            if stationName.upper() == s or stationName.lower() in stations[s][0]:
                stationName = s
                found=True
                break
        if not found:
            response_obj.messages_to_send.append("Sorry, I don't know that station.")
            logger.info("Sorry, I don't know that station.")
            return response_obj
        else:
            trains = get_trains(station=stationName)
            if trains:
                if line is not None and line.lower() in ['g','r','b','gold','red','green','blue','y','yellow','o','orange'] and direction is not None and direction.lower() in ['n','s','e','w','north','south','east','west','northbound','southbound','eastbound','westbound']:
                    if line.lower().startswith('r'):
                        line = 'RED'
                    elif line.lower().startswith('y') or line.lower().startswith('o') or line.lower().startswith('go'):
                        line = 'GOLD'
                    elif line.lower().startswith('b'):
                        line = 'BLUE'
                    elif line.lower().startswith('g'):
                        line = 'GREEN'
                    if direction.lower().startswith('n'):
                        direction = 'N'
                    elif direction.lower().startswith('s'):
                        direction = 'S'
                    elif direction.lower().startswith('e'):
                        direction = 'E'
                    elif direction.lower().startswith('w'):
                        direction = 'W'
                else:
                    line = None
                    direction = None
                final_trains = []
                if line:
                    for t in trains:
                        if t.line == line and t.direction == direction:
                            final_trains.append(t)
                else:
                    for t in trains:
                        final_trains.append(t)
                if final_trains:
                    final_message = ""
                    for t in final_trains:
                        final_message = final_message +  t.line.capitalize() + " line train to " + t.destination + " (" + t.direction + "): " + ("Arriving in " + t.waiting_time if t.waiting_time[0].isdigit() else t.waiting_time) + "\n"
                    await ctx.send(final_message)
                else:
                    await ctx.send("No trains in the near future.")
            else:
                print("No trains near that station.")
        
    def __init__(self, bot):
        self.bot = bot
        print("MARTA ready to go!")
        
def setup(bot):
    bot.add_cog(Plex(bot))
