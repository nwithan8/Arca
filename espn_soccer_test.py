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
pro_leagues = ['soccer']
college_leagues = ['ncf','ncb','ncw']
all_leagues = pro_leagues + college_leagues

followup = []

print("Beginning team download. A final dictionary will be available in \'espn_dict.txt\' when completed.\nWARNING: This process upwards of 10-15 minutes. Please be patient.\n")
# make master dict
leagues_string = "{"
for league in all_leagues:
    team_codes[str(league)] = {}
            
# grab codes for each team, store in league dicts, store in master dict
soup = BeautifulSoup(requests.get("http://www.espn.com/soccer/teams").content, features='lxml').findAll("select", {"class": "dropdown__select"})[0].findAll("option")
for l in soup:
    temp_dict = {}
    team_codes['soccer'][str(l['value'])] = 0
    soup2 = BeautifulSoup(requests.get("http://www.espn.com" + l['data-url']).content, features="lxml").findAll("section", {"class": "TeamLinks flex items-center"})
    bar = Bar('Loading ' + l['value'].upper() + ' teams', max=int(len(soup2)))
    for sec in soup2:
        try:
            temp_dict[str(re.search('/id/(.*)/', str(sec.a.get('href'))).group(1))] = sec.find("img", {"class": "aspect-ratio--child"}).get('title')
        except (TypeError, AttributeError):
            followup.append([league, sec.a.get('href')])
        bar.next()
    team_codes['soccer'][str(l['value'])] = temp_dict
    
print("Completed first pass. Checking follow-up...")

if followup:
    print("Doing second pass on " + str(len(followup)) + " teams...")
    for f in followup:
        soup = BeautifulSoup(requests.get("http://www.espn.com" + f[1]).content)
        team_id = str(re.search('/500/(.*).png', str(soup.find("img", {"class":"aspect-ratio--object imageLoaded lazyloaded"})['src'])).group(1))
        name = soup.find("span", {"class": "ClubhouseHeader__Location"}).text
        mascot = soup.find("span", {"class": "ClubhouseHeader__DisplayName"}).text
        vals = [name + " " + mascot, name, mascot]
        team_codes['soccer'][str(f[0])].update({"'" + str(team_id) + "'" : vals})
        
print(team_codes)
            
            #id = str(re.search('/id/(.*)/', BeautifulSoup(requests.get("http://www.espn.com" + f[1]).content).find("img", {"class":"aspect-ratio--object imageLoaded lazyloaded"})
            #name = BeautifulSoup(requests.get("http://www.espn.com" + f[1]).content).find("div", {"class":"ClubhouseHeader__Content"})['src']).group(1))
            #print(id)
            #team_codes[str(f[0])].update( {"'" + str(re.search('/id/(.*)/', str(BeautifulSoup(requests.get("http://www.espn.com" + f[1]).content).find("div", {"class":"ClubhouseHeader__Content"}).group(1)) + "'": vvvvvvvvvvv
