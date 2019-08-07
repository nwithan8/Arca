from discord.ext import commands, tasks
import discord
import urllib
from urllib import request
import urllib.request
import re
from bs4 import BeautifulSoup
import requests
from collections import defaultdict
import json

team_codes={}

pro_leagues = ['nfl','mlb','nba','nhl','wnba']
college_leagues = ['ncf','ncb','ncw']
all_leagues = pro_leagues + college_leagues

#Future support: 'tennis', 'soccer'

class Team(object):
    def __init__(self, first_name, second_name, code, initials):
        self.full_name = first_name + " " + second_name
        self.code = code
        self.initials = initials

class ESPN(commands.Cog):
        
    def fix_league(self, league):
        league = league.lower()
        if (league == "cfb"):
            league = "ncf"
        if (league == "cbbm"):
            league = "ncb"
        if (league == "cbbw"):
            league = "ncw"
        return league
    
    def get_scores(self, league):
        #LEAGUE STRINGS
        NCAA_FB = 'ncf'
        NCAA_BBM = 'ncb'
        NCAA_BBW = 'ncw'
        NFL = 'nfl'
        MLB = 'mlb'
        NBA = 'nba'
        NHL = 'nhl'
        WNBA = 'wnba'
        TENNIS = 'tennis'
        SOCCER = 'soccer'
        
        
        #Credit to Josh Fuerst (http://www.fuerstjh.com) for creating his makeshift ESPN API after the official one was locked.
        scores = {}
        STRIP = "1234567890 "
        STRIP_BRACES = "()1234567890 "
        #visit espn bottomline website to get scores as html page
        url = 'http://www.espn.com/'+league+'/bottomline/scores'
        req = urllib.request.Request(url)
        response = urllib.request.urlopen(req)
        page = response.read()
        #url decode the page and split into list
        data = urllib.request.unquote(str(page))
        #t = re.search('_s_count.*$',data)
        data = re.sub('&'+league+"_s_count.*$","",data)
        data = data.split('&'+league+'_s_left')
        data[0]=""
        #print(data)
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
            team1_rank = ''
            team1_score = '0'
            team2_name = ''
            team2_rank = ''
            team2_score = '0'
                                
            if (' at ' not in score):
                teams = score.split('  ')
                team1_name = teams[0][0:teams[0].rfind(' ')].lstrip(STRIP)
                team2_name = teams[1][0:teams[1].rfind(' ')].lstrip(STRIP)
                team1_score = teams[0][teams[0].rfind(' ')+1:].strip()
                team2_score = teams[1][teams[1].rfind(' ')+1:].strip()
                if ') ' in team1_name:
                    team1_rank = re.search('\((\d*)\)',team1_name).group(1)
                    team1_name = team1_name.lstrip(STRIP_BRACES)
                if ') ' in team2_name:
                    team2_rank= re.search('\((\d*)\)',team2_name).group(1)
                    team2_name = team2_name.lstrip(STRIP_BRACES)
            else:
                teams = score.split(' at ')
                team1_name = teams[0].lstrip(STRIP)
                team2_name = teams[1].lstrip(STRIP)
                if ') ' in team1_name:
                    team1_rank = re.search('\((\d*)\)',team1_name).group(1)
                    team1_name = team1_name.lstrip(STRIP_BRACES)
                if ') ' in team2_name:
                    team2_rank= re.search('\((\d*)\)',team2_name).group(1)
                    team2_name = team2_name.lstrip(STRIP_BRACES)
                                        
            #add to return dictionary
            scores[gameID] = ['','','','','','','']
            scores[gameID][0] = team1_name
            scores[gameID][1] = team1_rank
            scores[gameID][2] = team1_score
            scores[gameID][3] = team2_name
            scores[gameID][4] = team2_rank
            scores[gameID][5] = team2_score
            scores[gameID][6] = time
        return scores
    
    @tasks.loop(count=1)
    #@commands.command(name="teams")
    async def teams(self):
        # make master dict
        leagues_string = "{"
        for league in all_leagues:
            team_codes[str(league)] = 0
        
        # grab codes for each team, store in league dicts, store in master dict
        for league in pro_leagues:
            temp_dict = {}
            soup = BeautifulSoup(requests.get("http://www.espn.com/" + league + "/teams").content)
            for sec in soup.findAll("section", {"class": "TeamLinks flex items-center"}):
                temp_dict[str(re.search('/name/(.*)/', str(sec.a.get('href'))).group(1))] = sec.find("img", {"class": "aspect-ratio--child"}).get('title')
            team_codes[league] = temp_dict
            
        # same, but college has numbers rather than initials as codes
        for league in college_leagues:
            temp_dict = {}
            soup = BeautifulSoup(requests.get("http://www.espn.com/" + league + "/teams").content)
            for sec in soup.findAll("section", {"class": "TeamLinks flex items-center"}):
                temp_dict[str(re.search('/id/(.*)/', str(sec.a.get('href'))).group(1))] = sec.find("img", {"class": "aspect-ratio--child"}).get('title')
            team_codes[league] = temp_dict
            
        print("Teams updated.")
        print("ESPN ready.")

    @commands.group(aliases=["ESPN"])
    async def espn(self, ctx: commands.Context):
        """
        Get live info from ESPN.com
        """
        if ctx.invoked_subcommand is None:
            await ctx.send("What subcommand?")
        
    @espn.command(name="prob")
    async def espn_prob(self, ctx: commands.Context, league: str, *, team: str):
        """
        ESPN's "win probability" for a team's current game
        Supported leagues: NFL, NBA, MLB, NHL, CFB, CBBW
        """
        league = self.fix_league(league)
        try:
            scores = self.get_scores(league)
            if not scores:
                await ctx.send("Oops, there's no " + league.upper() + " games!")
            else:
                searched_id = ""
                for g in scores:
                        if (scores[g][0].lower().strip() == team.lower().strip()) or (scores[g][3].lower().strip() == team.lower().strip()):
                            searched_id = g
                            break
                embed = discord.Embed(title=("(" + scores[searched_id][1] + ") " if scores[searched_id][1] != '' else '') + scores[searched_id][0] + " " + scores[searched_id][2] + " - " + ("(" + scores[searched_id][4] + ") " if scores[searched_id][4] != '' else '') + scores[searched_id][3] + " " + scores[searched_id][5] + " " + scores[searched_id][6])
                embed.set_thumbnail(url="https://image.flaticon.com/icons/png/128/870/870901.png")
                try:
                    soup = BeautifulSoup(requests.get("http://www.espn.com/"+league+"/game?gameId=" + str(searched_id)).content)
                    probholder = soup.find("span", {"class": "header-win-percentage"})
                    if not probholder:
                        await ctx.send("Couldn't find that game.")
                    else:
                        prob = probholder.find("img").nextSibling.strip().replace('%','')
                        team_id = re.search('/500/(.*).png&amp', str(probholder)).group(1)
                        if float(prob) < 100:
                            embed.add_field(name="The " + team_codes[league][team_id] + " have a " + prob + "% chance of winning.", value="http://www.espn.com/"+league+"/game?gameId="+str(searched_id),inline=False)
                        else:
                            embed.add_field(name="The " + team_codes[league][team_id] + " won.", value="http://www.espn.com/"+league+"/game?gameId="+str(searched_id),inline=False)
                        await ctx.send(embed=embed)
                except:
                    await ctx.send("Sorry, couldn't reach ESPN.com")
        except Exception as e:
            print(str(e))
            await ctx.send("Something went wrong. Please try again.")
            
    @espn_prob.error
    async def espn_prob_error(self, ctx, error):
        await ctx.send("Please include <league> <team>")
        
    @espn.command(name="top")
    async def espn_top(self, ctx: commands.Context, league: str):
        """
        Top ranked teams of a specific league
        Supported leagues: CFB
        """
        league=self.fix_league(league)
        if league in ['ncf']:
            try:
                scores=self.get_scores(league)
                if not scores:
                    await ctx.send("Oops there's no " + league.upper() + " games!")
                else:
                    embed = discord.Embed(title="Top Teams")
                    embed.set_thumbnail(url="https://image.flaticon.com/icons/png/128/870/870901.png")
                    respond = False
                    games = ""
                    page_count = 1;
                    ranking = 1
                    fc = 0
                    top_games = {
                        }
                    for g in scores:
                        if scores[g][1] != '' or scores[g][4] != '':
                            if scores[g][1] != '' and scores[g][4] != '':
                                top_games[min(scores[g][1],scores[g][4])] = ['','']
                                top_games[min(scores[g][1],scores[g][4])][0] = str(g)
                                top_games[min(scores[g][1],scores[g][4])][1] = scores[g]
                            else:
                                top_games[max(scores[g][1],scores[g][4])] = ['','']
                                top_games[max(scores[g][1],scores[g][4])][0] = str(g)
                                top_games[max(scores[g][1],scores[g][4])][1] = scores[g]
                    for i in range(1,26):
                        if str(i) in top_games:
                            embed.add_field(name=("(" + top_games[str(i)][1][1] + ") " if top_games[str(i)][1][1] != '' else '') + ("**"+top_games[str(i)][1][0]+"** " if int(top_games[str(i)][1][2]) > int(top_games[str(i)][1][5]) else top_games[str(i)][1][0]+" ")+top_games[str(i)][1][2]+" - "+ ("(" + top_games[str(i)][1][4] + ") " if top_games[str(i)][1][4] != '' else '') + ("**"+top_games[str(i)][1][3]+"** " if int(top_games[str(i)][1][5]) > int(top_games[str(i)][1][2]) else top_games[str(i)][1][3]+" ")+top_games[str(i)][1][5],value=top_games[str(i)][1][6]+("" if not str(top_games[str(i)][0])[0].isdigit() else " - [Live](http://www.espn.com/"+league+"/game?gameId="+top_games[str(i)][0]+")"),inline=False)
                            #print(top_games[str(i)])
                    await ctx.send(embed=embed)
            except Exception as e:
                print(str(e))
                await ctx.send("Something went wrong. Please try again.")
        else:
            await ctx.send("Please try another league.")
            
    @espn_top.error
    async def espn_top_error(self, ctx, error):
        await ctx.send("Please include <league>")
        
    @espn.command(name="score")
    async def espn_score(self, ctx: commands.Context, league: str, *, team: str):
        """
        Live score of a team's current game
        Use team name, or 'all' to get all current games
        Supported leagues: NFL, NBA, MLB, NHL, CFB, CBBM, CBBW
        """
        league = self.fix_league(league)
        try:
            scores = self.get_scores(league)
            if not scores:
                await ctx.send("Oops, there's no " + league.upper() + " games!")
            else:
                embed = discord.Embed(title="ESPN Scoreboard")
                embed.set_thumbnail(url="https://image.flaticon.com/icons/png/128/870/870901.png")
                respond = False
                games = ""
                page_count = 1
                if team == 'all':
                    fc = 0
                    for g in scores:
                        embed.add_field(name=("(" + scores[g][1] + ") " if scores[g][1] != '' else '') + ("**"+scores[g][0]+"** " if int(scores[g][2]) > int(scores[g][5]) else scores[g][0]+" ")+scores[g][2]+" - "+ ("(" + scores[g][4] + ") " if scores[g][4] != '' else '') + ("**"+scores[g][3]+"** " if int(scores[g][5]) > int(scores[g][2]) else scores[g][3]+" ")+scores[g][5],value=scores[g][6]+("" if not str(g)[0].isdigit() else " - [Live](http://www.espn.com/"+league+"/game?gameId="+g+")"),inline=False)
                        fc = fc + 1
                        if fc >= 23:
                            embed.add_field(name='\u200b',value="http://www.espn.com/"+league+"/scoreboard",inline=False)
                            embed.title = "ESPN Scoreboard (Page " + str(page_count) + ")"
                            page_count = page_count + 1
                            await ctx.send(embed=embed)
                            embed = discord.Embed(title="ESPN Scoreboard (Page " + str(page_count) + ")")
                            embed.set_thumbnail(url="https://image.flaticon.com/icons/png/128/870/870901.png")
                            fc = 0
                        if len(embed) > 5900:
                            embed.add_field(name='\u200b',value="http://www.espn.com/"+league+"/scoreboard",inline=False)
                            embed.title = "ESPN Scoreboard (Page " + str(page_count) + ")"
                            page_count = page_count + 1
                            await ctx.send(embed=embed)
                            embed = discord.Embed(title="ESPN Scoreboard (Page " + str(page_count) + ")")
                            embed.set_thumbnail(url="https://image.flaticon.com/icons/png/128/870/870901.png")
                    embed.add_field(name='\u200b',value="http://www.espn.com/"+league+"/scoreboard",inline=False)
                    respond = True
                else:
                    for g in scores:
                        if (scores[g][0].lower().strip() == team.lower().strip()) or (scores[g][3].lower().strip() == team.lower().strip()):
                            embed.add_field(name=("(" + scores[g][1] + ") " if scores[g][1] != '' else '') + ("**"+scores[g][0]+"** " if int(scores[g][2]) > int(scores[g][5]) else scores[g][0]+" ")+scores[g][2]+" - "+ ("(" + scores[g][4] + ") " if scores[g][4] != '' else '') + ("**"+scores[g][3]+"** " if int(scores[g][5]) > int(scores[g][2]) else scores[g][3]+" ")+scores[g][5],value=scores[g][6]+("" if not str(g)[0].isdigit() else " - [Live](http://www.espn.com/"+league+"/game?gameId="+g+")"),inline=False)
                            #if not scores[g][6][1].isdigit():
                            #embed.add_field(name='\u200b',value="http://www.espn.com/"+league+"/boxscore?gameId="+g,inline=False)
                            respond = True
                            break
                if not respond:
                    await ctx.send("That team wasn't found. Either they aren't playing, or the name is incorrect.\nTry again with a different team name (i.e. \"Boston\", not \"Red Sox\").\nFor multi-word names, use quotes, such as \"San Francisco\"")
                else:
                    await ctx.send(embed=embed)
        except Exception as e:
            print(str(e))
            await ctx.send("Something went wrong. Please try again.")
            
    @espn_score.error
    async def espn_score_error(self, ctx, error):
        await ctx.send("Please include <league> <team>")
            
    @espn.command(name="sched",aliases=["schedule"])
    async def espn_sched(self, ctx: commands.Context, league: str, *, team: str):
        """
        A link to a team's schedule
        Supported leagues: NFL, NBA, MLB, NHL
        """
        league = self.fix_league(league)
        team_id = None
        team_name = None
        for t, c in team_codes[league].items():
            if team.lower() in c.lower():
                team_name = c
                team_id = t
                break
        if team_id == None:
            await ctx.send("Couldn't find that team.")
        else:
            await ctx.send(team_name + " schedule: http://www.espn.com/" + league + "/team/schedule/_/name/"+team_id)
            #try:
            #    soup = BeautifulSoup(requests.get("http://www.espn.com/"+league+"/team/schedule/_/name/" + str(searched_id)).content)
            #    raw_schedule = soup.find("tbody", {"class": "Table2__tbody"})
            #    if not raw_schedule:
            #        await ctx.send("Couldn't find that team's schedule.")
            #    else:
            #        print(raw_schedule)
            #        for sec in raw_schedule.findAll("tr", {"class":"Table2__tr Table2__tr--sm Table2__even"}):
            #            print(sec.get(
            #except:
            #    await ctx.send("Sorry, couldn't reach ESPN.com")
            
    @espn_sched.error
    async def espn_sched_error(self, ctx, error):
        await ctx.send("Please include <league> <team>")
        
    def __init__(self, bot):
        self.bot = bot
        print("ESPN - updating teams...")
        self.teams.start()
