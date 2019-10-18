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

team_id = "ne"
league = 'nfl'

table = BeautifulSoup(requests.get("http://www.espn.com/" + league + "/team/schedule/_/" + ("name/" if league in pro_leagues else "id/") + str(team_id)).content, features="lxml").find('tbody',{"class":"Table2__tbody"}).findAll('tr')
week_count = 0
for row in table:
    cols = row.findAll("td",{"class":"Table2__td"})
    if league == 'nfl':
        if cols[0].text.isdigit():
            if int(cols[0].text) < week_count:
                break
            week_count = int(cols[0].text)
            print(cols[0].text)
            print(cols[1].text)
            if "bye" not in cols[1].text.lower():
                print(cols[2].text)
                print(cols[3].text)
    else:
        if any(v in cols[0].text.lower() for v in ['sun','mon','tue','wed','thu','fri','sat']):
            print(cols[0].text)
            print(cols[1].text)
            if "bye" not in cols[1].text.lower():
                print(cols[2].text)
