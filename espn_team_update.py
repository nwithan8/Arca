#!/usr/bin/python3

import urllib
from urllib import request
import urllib.request
import re
from bs4 import BeautifulSoup
import requests
from collections import defaultdict
import json
from progress.bar import Bar

team_codes={}
pro_leagues = ['nfl','mlb','nba','wnba'] # NHL doesn't want to play nice with its headers HTML code
college_leagues = ['ncf','ncb','ncw']
all_leagues = pro_leagues + college_leagues

followup = []

print("Beginning team download. A final dictionary will be available in \'espn_dict.txt\' when completed.\nWARNING: This process upwards of 10-15 minutes. Please be patient.\n")

with open('espn/espn_dict.txt', 'r') as f:
    team_codes = eval(f.read())
f.close()

# make master dict
leagues_string = "{"
            
# grab codes for each team, store in league dicts, store in master dict
for league in pro_leagues: # Looking for 'name'
    temp_dict = {}
    soup = BeautifulSoup(requests.get("http://www.espn.com/" + league + "/teams").content, features='lxml').findAll("section", {"class": "TeamLinks flex items-center"})
    bar = Bar('Loading ' + league.upper() + ' teams', max=int(len(soup)))
    for sec in soup:
        soup2 = BeautifulSoup(requests.get("http://www.espn.com" + sec.a.get('href')).content, features='lxml')
        try:
            temp_dict[str(re.search('/name/(.*)/', str(sec.a.get('href'))).group(1))] = [sec.find("img", {"class": "aspect-ratio--child"}).get('title'), soup2.find("span", {"class": "ClubhouseHeader__Location"}).text, soup2.find("span", {"class": "ClubhouseHeader__DisplayName"}).text]
        except (TypeError, AttributeError):
            followup.append([league, sec.a.get('href')])
        bar.next()
    team_codes[league] = temp_dict
    
print(team_codes)
print("Completed first pass. Checking follow-up...")

if followup:
    print("Doing second pass on " + str(len(followup)) + " teams...")
    bar = Bar('Catching missed teams', max=int(len(followup)))
    for f in followup:
        print(f[1])
        soup = BeautifulSoup(requests.get("http://www.espn.com" + f[1]).content, features='lxml')
        print(str(soup.find("img", {"class":"aspect-ratio--object imageLoaded lazyloaded"})['src']))
        team_id = str(re.search('/500/(.*).png', str(soup.find("img", {"class":"aspect-ratio--object imageLoaded lazyloaded"})['src'])).group(1))
        name = soup.find("span", {"class": "ClubhouseHeader__Location"}).text
        mascot = soup.find("span", {"class": "ClubhouseHeader__DisplayName"}).text
        vals = [name + " " + mascot, name, mascot]
        team_codes[str(f[0])].update({"'" + str(team_id) + "'" : vals})
        bar.next()
            
            #id = str(re.search('/id/(.*)/', BeautifulSoup(requests.get("http://www.espn.com" + f[1]).content).find("img", {"class":"aspect-ratio--object imageLoaded lazyloaded"})
            #name = BeautifulSoup(requests.get("http://www.espn.com" + f[1]).content).find("div", {"class":"ClubhouseHeader__Content"})['src']).group(1))
            #print(id)
            #team_codes[str(f[0])].update( {"'" + str(re.search('/id/(.*)/', str(BeautifulSoup(requests.get("http://www.espn.com" + f[1]).content).find("div", {"class":"ClubhouseHeader__Content"}).group(1)) + "'":
        
with open('espn/espn_dict.txt', 'w') as f:
    f.write(str(team_codes))
f.close()
