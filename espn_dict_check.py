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

with open('espn_dict.txt', 'r') as f:
    team_codes = eval(f.read())
f.close()

pro_leagues = ['nfl','mlb','nba','nhl','wnba','soccer']
college_leagues = ['ncf','ncb','ncw']
all_leagues = pro_leagues + college_leagues

followup = []

for l in all_leagues:
    #soup = BeautifulSoup(requests.get("http://www.espn.com/" + l + "/teams").content).findAll("section", {"class": "TeamLinks flex items-center"})
    soup = []
    if len(soup) != len(team_codes[l]):
        print("Missing " + l.upper() + " teams! " + str(len(soup)) + " - ESPN, " + str(len(team_codes[l])) + " - file")
    else:
        print("Number of " + l.upper() + " teams: " + str(len(team_codes[l])))
