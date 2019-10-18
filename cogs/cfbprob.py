from discord.ext import commands
import html
from bs4 import BeautifulSoup, SoupStrainer
from bs4.element import Comment
import requests
import re
import httplib2
import urllib
import os
import mysql.connector


class CFBProb(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot
        
     # Main
    @commands.command(name="cfbprob",pass_context=True,no_pm=True)
    async def _cfbprob(self, ctx, *, team):
        hostname='localhost'
        username='cfbprob'
        password='cfbprob'
        database='cfbprob'

        http = httplib2.Http()
        http.force_exception_to_status_code = False
        #find the team
        async def searchteam(team, failedTwice):
            conn = mysql.connector.connect(host=hostname,username=username,passwd=password,db=database)
            cur = conn.cursor(buffered=True)
            cur.execute("SELECT gameid FROM games WHERE teamname = '" + str(team) + "'")
            value = ""
            if cur.fetchall():
                value = str(max(cur.fetchall))
                cur.close()
            else:
                failedTwice += 1
                cur.close()
                if failedTwice < 2:
                    dict = await get_scores('college-football')
                    if dict != None:
                        for gameid, teams_and_scores in dict.items():
                            await addgame(gameid, teams_and_scores[0])
                            await addgame(gameid, teams_and_scores[2])
                        value = await searchteam(team, failedTwice)
                    else:
                        value = -1
                else:
                    failedTwice = 0
                    value = 0
            conn.close()
            return value

        # get game info
        async def getinfo(gameId):
            try:
                status, response = http.request(base + str(gameId))
                soup = BeautifulSoup(response, 'html.parser')
                probholder = soup.findAll("span", {"class": "header-win-percentage"})
                if not probholder:
                    return "No game found."
                else:
                    soup2 = BeautifulSOup(str(probholder), 'html.parser')
                    prob = await whatprob(soup2)
                    if float(prob) < 100:
                        return (await whatteam(soup2)) + " has a " + prob + "% chance of winning, according to ESPN."
                    else:
                        return (await whatteam(soup2)) + " won."
            except httplib2.ServerNotFoundError:
                return "Could not reach ESPN."

        #add a game to db
        async def addgame(gameid, team):
            team = team.replace("'","")
            conn = mysql.connector.connect(host=hostname,username=username,passwd=password,db=database)
            cur = conn.cursor(buffered=True)
            cur.execute("INSERT IGNORE INTO games (gameid, teamname) VALUES ('" + str(gameid) + "','" + team + "')")
            conn.commit()
            cur.close()
            conn.close()

        #get a score
        async def get_scores(league):
            scores = {}
            STRIP = "()1234567890 "
            try:
                req = urllib.request.Request('http://www.espn.com/'+league+'/bottomline/scores')
                response = urllib.request.urlopen(req)
                page = str(response.read()).replace('&ncf_s_loaded','&ncf_s_left')
                data = urllib.request.unquote(str(page)).split('&ncf_s_left')
                data[0] = ""
                for i in range(1,len(data)):
                    #get rid of junk at beginning of line, remove ^ which marks team with ball
                    main_str = data[i][data[i].find('=')+1:].replace('^','')
                    #extract time, you can use the ( and ) to find time in string
                    time =  main_str[main_str.rfind('('):main_str.rfind(')')+1].strip()
                    #extract score, it should be at start of line and go to the first (
                    score =  main_str[0:main_str.rfind('(')].strip()
                    #extract espn gameID use the keyword gameId to find it
                    gameID = main_str[main_str.rfind('gameId')+7:].strip()

                    if gameID == '':
                        #something wrong happened
                        continue

                    #split score string into each teams string
                    team1_name = ''
                    team1_score = '0'
                    team2_name = ''
                    team2_score = '0'

                    if (' at ' not in score):
                        teams = score.split('  ')
                        team1_name = teams[0][0:teams[0].rfind(' ')].lstrip(STRIP)
                        team2_name = teams[1][0:teams[1].rfind(' ')].lstrip(STRIP)
                        team1_score = teams[0][teams[0].rfind(' ')+1:].strip()
                        team2_score = teams[1][teams[1].rfind(' ')+1:].strip()
                    else:
                        teams = score.split(' at ')
                        team1_name = teams[0].lstrip(STRIP)
                        team2_name = teams[1].lstrip(STRIP)

                    #add to return dictionary
                    scores[gameID] = ['','','','','']
                    scores[gameID][0] = team1_name
                    scores[gameID][1] = team1_score
                    scores[gameID][2] = team2_name
                    scores[gameID][3] = team2_score
                    scores[gameID][4] = time
                    return scores
            except Exception as e:
                print(str(e))

        # get team name
        async def whatteam(htmlcode):
            id = re.search('teamlogos/ncaa/500/(.*).png&amp', str(htmlcode))
            conn = mysql.connector.connect(host=hostname,username=username,passwd=password,db=database)
            cur = conn.cursor(buffered=True)
            cur.execute("SELECT teamname FROM ids WHERE teamid = " + str(id.group(1)))
            value = ""
            if cur.rowcount <= 0:
                status, response = http.request("http://www.espn.com/college-football/team/_/id/" + str(id.group(1)))
                soup = BeautifulSoup(response, 'html.parser')
                soup2 = BeautifulSoup(str(soup.findAll("span", {"class": "ClubhouseHeader__Location"}), 'html.parser'))
                for match in soup2.findAll('span'):
                    match.unwrap()
                await postquery(str(id.group(1)),str(soup2[0]))
                value =  str(soup2[0])
            else:
                value = cur.fetchone()[0]
            cur.close()
            conn.close()
            return value

        # grab probability
        async def whatprob(htmlcode):
            for match in htmlcode.findAll('span'):
                match.unwrap()
            for match in htmlcode.findAll('img'):
                match.unwrap()
            return str(htmlcode[0])

        # add id
        async def postquery(teamid, teamname):
            conn = mysql.connector.connect(host=hostname,username=username,passwd=password,db=database)
            cur = conn.cursor(buffered=True)
            cur.execute("INSERT IGNORE INTO ids (teamid, teamname) VALUES ('" + teamid + "','" + teamname + "')")
            conn.commit()
            cur.close()
            conn.close()
            
        #Check team's current chance of winning
        number = await searchteam(team, 0)
        response = ""
        if number > 0: #0 failed twice, -1 no football
            response = await getinfo(await searchteam(team))
        else:
            response = "D'oh, there's no football right now!"
        await ctx.send(response)


def setup(bot):
    bot.add_cog(CFBProb(bot))
