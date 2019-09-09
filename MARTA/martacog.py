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
    "https://itsmarta.com/Airport.aspx",
    -16,
    'ns'
  ],
  "ARTS CENTER STATION": [
    [
      'artscenter'
    ],
    "1255 West Peachtree St Atlanta, GA 30309",
    "https://itsmarta.com/Arts-Center.aspx",
    6,
    'ns'
  ],
  "ASHBY STATION": [
    [
      'ashby'
    ],
    "65 Joseph E Lowery Blvd Atlanta, GA 30314",
    "https://itsmarta.com/Ashby.aspx",
    -3,
    'ew'
  ],
  "AVONDALE STATION": [
    [
      'avondale'
    ],
    "915 E Ponce de Leon Ave Decatur, GA 30030",
    "https://itsmarta.com/Avondale.aspx",
    15,
    'ew'
  ],
  "BANKHEAD STATION": [
    [
      'bankhead'
    ],
    "1335 Donald Hollowell Pkwy Atlanta, GA 30318",
    "https://itsmarta.com/Bankhead.aspx",
    -9,
    'ew'
  ],
  "BROOKHAVEN STATION": [
    [
      'brookhaven'
    ],
    "4047 Peachtree Road, NE Atlanta, GA 30319",
    "https://itsmarta.com/Brookhaven.aspx",
    17,
    'ns'
  ],
  "BUCKHEAD STATION": [
    [
      'buckhead'
    ],
    "3360 Peachtree Rd, NE Atlanta, GA 30326",
    "https://itsmarta.com/Buckhead.aspx",
    16,
    'ns'
  ],
  "CHAMBLEE STATION": [
    [
      'chamblee'
    ],
    "5200 New Peachtree Road Chamblee, GA 30341",
    "https://itsmarta.com/Chamblee.aspx",
    21,
    'ns'
  ],
  "CIVIC CENTER STATION": [
    [
      'civiccenter'
    ],
    "435 West Peachtree St, NW Atlanta, GA 30308",
    "https://itsmarta.com/Civic-Center.aspx",
    2,
    'ns'
  ],
  "COLLEGE PARK STATION": [
    [
      'collegepark'
    ],
    "3800 Main St Atlanta, GA 30337",
    "https://itsmarta.com/College-Park.aspx",
    -15,
    'ns'
  ],
  "DECATUR STATION": [
    [
      'decatur'
    ],
    "400 Church St Decatur, GA 30030",
    "https://itsmarta.com/Decatur.aspx",
    13,
    'ew'
  ],
  "OMNI DOME STATION": [
    [
      'omnidome',
      'dome',
      'mercedesbenz',
      'mercedes-benz',
      'cnn',
      'statefarmarena',
      'philipsarena',
      'gwcc',
      'georgiaworldcongresscenter',
      'worldcongresscenter'
    ],
    "100 Centennial Olympic Park Atlanta, GA 30303",
    "https://itsmarta.com/Omni.aspx",
    -1,
    'ew'
  ],
  "DORAVILLE STATION": [
    [
      'doraville'
    ],
    "6000 New Peachtree Rd Doraville, GA 30340",
    "https://itsmarta.com/Doraville.aspx",
    24,
    'ns'
  ],
  "DUNWOODY STATION": [
    [
      'dunwoody'
    ],
    "1118 Hammond Dr Atlanta, GA 30328",
    "https://itsmarta.com/Dunwoody.aspx",
    22,
    'ns'
  ],
  "EAST LAKE STATION": [
    [
      'eastlake'
    ],
    "2260 College Ave Atlanta, GA 30307",
    "https://itsmarta.com/East-Lake.aspx",
    11,
    'ew'
  ],
  "EAST POINT STATION": [
    [
      'eastpoint'
    ],
    "2848 East Main St East Point, GA 30344",
    "https://itsmarta.com/East-Point.aspx",
    -12,
    'ns'
  ],
  "EDGEWOOD CANDLER PARK STATION": [
    [
      'edgewood',
      'candlerpark'
    ],
    "1475 DeKalb Ave, NE Atlanta, GA 30307",
    "https://itsmarta.com/Edgewood-Candler-Park.aspx",
    8,
    'ew'
  ],
  "FIVE POINTS STATION": [
    [
      'fivepoints',
      '5points'
    ],
    "30 Alabama St SW Atlanta, GA 30303",
    "https://itsmarta.com/Five-Points.aspx",
    0,
    'nsew'
  ],
  "GARNETT STATION": [
    [
      'garnett'
    ],
    "225 Peachtree St, SW Atlanta, GA 30303",
    "https://itsmarta.com/Garnett.aspx",
    -1,
    'ns'
  ],
  "GEORGIA STATE STATION": [
    [
      'georgiastate',
      'gsu',
      'school'
    ],
    "170 Piedmont Ave, SE Atlanta, GA 30303",
    "https://itsmarta.com/Georgia-State.aspx",
    1,
    'ew'
  ],
  "HAMILTON E HOLMES STATION": [
    [
      'hamiltoneholmes',
      'h.e.holmes',
      'heholmes'
    ],
    "70 Hamilton E Holmes Dr, NW Atlanta, GA 30311",
    "https://itsmarta.com/Hamilton-E-Holmes.aspx",
    -9,
    'ew'
  ],
  "INDIAN CREEK STATION": [
    [
      'indiancreek'
    ],
    "901 Durham Park Rd Stone Mountain, GA 30083",
    "https://itsmarta.com/Indian-Creek.aspx",
    20,
    'ew'
  ],
  "INMAN PARK STATION": [
    [
      'inman',
      'inmanpark'
    ],
    "055 DeKalb Ave, NE Atlanta, GA 30307",
    "https://itsmarta.com/Inman-Park.aspx",
    6,
    'ew'
  ],
  "KENSINGTON STATION": [
    [
      'kensington'
    ],
    "3350 Kensington Rd Decatur, GA 30032",
    "https://itsmarta.com/Kensington.aspx",
    18,
    'ew'
  ],
  "KING MEMORIAL STATION": [
    [
      'kingmemorial',
      'mlk'
    ],
    "377 Decatur St, SE Atlanta, GA 30312",
    "https://itsmarta.com/King-Memorial.aspx",
    3,
    'ew'
  ],
  "LAKEWOOD STATION": [
    [
      'lakewood'
    ],
    "2020 Lee St, SW Atlanta, GA 30310",
    "https://itsmarta.com/Lakewood.aspx",
    -8,
    'ns'
  ],
  "LENOX STATION": [
    [
      'lenox'
    ],
    "955 East Paces Ferry Rd, NE Atlanta, GA 30326",
    "https://itsmarta.com/Lenox.aspx",
    14,
    'ns'
  ],
  "LINDBERGH STATION": [
    [
      'lindbergh'
    ],
    "2424 Piedmont Rd, NE Atlanta, GA 30324",
    "https://itsmarta.com/Lindbergh.aspx",
    10,
    'ns'
  ],
  "MEDICAL CENTER STATION": [
    [
      'medicalcenter',
      'medcenter'
    ],
    "5711 Peachtree-Dunwoody Rd, NE Atlanta, GA 30342",
    "https://itsmarta.com/Medical-Center.aspx",
    20,
    'ns'
  ],
  "MIDTOWN STATION": [
    [
      'midtown'
    ],
    "41 Tenth St, NE Atlanta, GA 30309",
    "https://itsmarta.com/Midtown.aspx",
    4,
    'ns'
  ],
  "NORTH AVE STATION": [
    [
      'northave',
      'northavenue',
      'gt',
      'georgiatech',
      'tech'
    ],
    "713 West Peachtree St, NW Atlanta, GA 30308",
    "https://itsmarta.com/North-Ave.aspx",
    3,
    'ns'
  ],
  "NORTH SPRINGS STATION": [
    [
      'northsprings'
    ],
    "7010 Peachtree Dunwoody Rd Sandy Springs, GA 30328",
    "https://itsmarta.com/North-Springs.aspx",
    27,
    'ns'
  ],
  "OAKLAND CITY STATION": [
    [
      'oakland',
      'oaklandcity'
    ],
    "1400 Lee St, SW Atlanta, GA 30310",
    "https://itsmarta.com/Oakland-City.aspx",
    -6,
    'ns'
  ],
  "PEACHTREE CENTER STATION": [
    [
      'peachtreecenter'
    ],
    "216 Peachtree St, NE Atlanta, GA 30303",
    "https://itsmarta.com/Peachtree-Center.aspx",
    1,
    'ns'
  ],
  "SANDY SPRINGS STATION": [
    [
      'sandysprings'
    ],
    "1101 Mount Vernon Hwy Atlanta, GA 30338",
    "https://itsmarta.com/Sandy-Springs.aspx",
    25,
    'ns'
  ],
  "VINE CITY STATION": [
    [
      'vinecity'
    ],
    "502 Rhodes St, NW Atlanta, GA 30314",
    "https://itsmarta.com/Vine-City.aspx",
    -2,
    'ew'
  ],
  "WEST END STATION": [
    [
      'westend'
    ],
    "680 Lee St, SW Atlanta, GA 30310",
    "https://itsmarta.com/West-End.aspx",
    -4,
    'ns'
  ],
  "WEST LAKE STATION": [
    [
      'westlake'
    ],
    "80 Anderson Ave, SW Atlanta, GA 30314",
    "https://itsmarta.com/West-Lake.aspx",
    -6,
    'ew'
  ]
}
    
class MARTA(commands.Cog):
            
    @commands.group(aliases=["MARTA"], pass_context=True)
    async def marta(self, ctx: commands.Context):
        """
        MARTA commands
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What about it?")
            
    @marta.command(name="trains", pass_context=True)
    async def marta_trains(self, ctx: commands.Context, station: str=None, line: str=None, direction: str=None):
        """
        Get live train schedules
        Optional: 'line' (Red, Gold, Blue, Green) and 'direction' (N, S, E, W)
        Must include both 'line' and 'direction'
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
    
    @marta.command(name="time", pass_context=True)
    async def marta_time(self, ctx: commands.Context, startPoint: str, endPoint: str):
        """
        Get travel time between two stations
        """
        valid_start = False
        valid_end = False
        for s in stations:
            if startPoint.upper() == s or startPoint.lower() in stations[s][0]:
                startPoint = s
                valid_start = True
            if endPoint.upper() == s or endPoint.lower() in stations[s][0]:
                endPoint = s
                valid_end = True
        if not valid_start:
            await ctx.send("That starting station does not exist.")
        elif not valid_end:
            await ctx.send("That ending station does not exist.")
        else:
            time = 0
            if (stations[startPoint][4] != stations[endPoint][4]): # one is ns, other is ew (5points is nsew, but time = 0, so not effect)
                # s -> 5 + 5 -> e
                time = abs(stations[startPoint][3]) + abs(stations[endPoint][3])
            else:
                # both on same track, so s - e
                time = abs(stations[startPoint][3] - stations[endPoint][3])
            await ctx.send("It takes approximately " + str(time) + (" minutes" if time > 1 else " minute") + " to go from " + startPoint.title() + " to " + endPoint.title())
            
        
    @marta_time.error
    async def marta_time_error(self, ctx, error):
        await ctx.send("Please include an existing starting and ending station.")
        
    @marta.command(name="stations", pass_context=True)
    async def marta_stations(self, ctx: commands.Context):
        """
        List available stations and nicknames
        """
        response = ""
        for s in stations:
            response = response + s + ": "
            for n in stations[s][0]:
                response = response + n + ", "
            response = response[:-1] + "\n"
        await ctx.send(response)
        
        
    def __init__(self, bot):
        self.bot = bot
        print("MARTA ready to go!")
        
def setup(bot):
    bot.add_cog(Plex(bot))
