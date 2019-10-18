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
pro_leagues = ['nfl','mlb','nba','nhl','wnba']
college_leagues = ['ncf','ncb','ncw']
all_leagues = pro_leagues + college_leagues

followup = []

print("Beginning team download. A final dictionary will be available in \'espn_dict.txt\' when completed.\nWARNING: This process upwards of 10-15 minutes. Please be patient.\n")
# make master dict
leagues_string = "{"
for league in all_leagues:
    team_codes[str(league)] = 0
            
# grab codes for each team, store in league dicts, store in master dict
for league in pro_leagues:
    temp_dict = {}
    soup = BeautifulSoup(requests.get("http://www.espn.com/" + league + "/teams").content).findAll("section", {"class": "TeamLinks flex items-center"})
    bar = Bar('Loading ' + league.upper() + ' teams', max=int(len(soup)))
    for sec in soup:
        try:
            temp_dict[str(re.search('/name/(.*)/', str(sec.a.get('href'))).group(1))] = sec.find("img", {"class": "aspect-ratio--child"}).get('title')
        except (TypeError, AttributeError):
            followup.append([league, sec.a.get('href')])
        bar.next()
    team_codes[league] = temp_dict
    
# same, but college has numbers rather than initials as codes
for league in college_leagues:
    temp_dict = {}
    soup = BeautifulSoup(requests.get("http://www.espn.com/" + league + "/teams").content).findAll("section", {"class": "TeamLinks flex items-center"})
    bar = Bar('Loading ' + league + ' teams', max=int(len(soup)))
    for sec in soup:
        soup2 = BeautifulSoup(requests.get("http://www.espn.com" + sec.a.get('href')).content)
        try:
            temp_dict[str(re.search('/id/(.*)/', str(sec.a.get('href'))).group(1))] = [sec.find("img", {"class": "aspect-ratio--child"}).get('title'), soup2.find("span", {"class": "ClubhouseHeader__Location"}).text, soup2.find("span", {"class": "ClubhouseHeader__DisplayName"}).text]
        except (TypeError, AttributeError):
            followup.append([league, sec.a.get('href')])
        bar.next()
    team_codes[league] = temp_dict
    
print("Completed first pass. Checking follow-up...")

if followup:
    print("Doing second pass on " + str(len(followup)) + " teams...")
    for f in followup:
        soup = BeautifulSoup(requests.get("http://www.espn.com" + f[1]).content)
        team_id = str(re.search('/500/(.*).png', str(soup.find("img", {"class":"aspect-ratio--object imageLoaded lazyloaded"})['src'])).group(1))
        name = soup.find("span", {"class": "ClubhouseHeader__Location"}).text
        mascot = soup.find("span", {"class": "ClubhouseHeader__DisplayName"}).text
        vals = [name + " " + mascot, name, mascot]
        team_codes[str(f[0])].update({"'" + str(team_id) + "'" : vals})
            
            #id = str(re.search('/id/(.*)/', BeautifulSoup(requests.get("http://www.espn.com" + f[1]).content).find("img", {"class":"aspect-ratio--object imageLoaded lazyloaded"})
            #name = BeautifulSoup(requests.get("http://www.espn.com" + f[1]).content).find("div", {"class":"ClubhouseHeader__Content"})['src']).group(1))
            #print(id)
            #team_codes[str(f[0])].update( {"'" + str(re.search('/id/(.*)/', str(BeautifulSoup(requests.get("http://www.espn.com" + f[1]).content).find("div", {"class":"ClubhouseHeader__Content"}).group(1)) + "'":
        
with open('espn_dict.txt', 'w') as f:
    f.write(str(team_codes))
    f.close()
