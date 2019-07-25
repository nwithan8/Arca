from discord.ext import commands
import discord
import urllib
from urllib import request
import urllib.request
import re

class ESPNScores(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    """
    Get live sports scores from ESPN.com
    """

    help_msg = "This is a test of the help section."

    @commands.command(name="espn",help=help_msg,pass_context=True,no_pm=True,case_insensitive=True)
    @commands.bot_has_permissions(embed_links=True)
    async def _espn(self, ctx, league: str, team: str):
    
        #LEAGUE STRINGS
        NCAA_FB = 'ncf'
        NCAA_BB = 'ncb'
        NFL = 'nfl'
        MLB = 'mlb'
        NBA = 'nba'
        NHL = 'nhl'
        
        async def on_command_error(self,error,ctx):
            print("Got the error!")

        async def get_game(team, league, game_list):
            embed = discord.Embed(title="ESPN Scoreboard")
            respond = False
            games = ""
            if team == 'all':
                for g in game_list:
                    embed.add_field(name=("**"+game_list[g][0]+"** " if int(game_list[g][1]) > int(game_list[g][3]) else game_list[g][0]+" ")+game_list[g][1]+" - "+("**"+game_list[g][2]+"** " if int(game_list[g][3]) > int(game_list[g][1]) else game_list[g][2]+" ")+game_list[g][3]+" *"+game_list[g][4]+"*",value='\u200b',inline=False)
                embed.add_field(name="http://www.espn.com/"+league+"/scoreboard",value='\u200b',inline=False)
                respond = True
            else:
                for g in game_list:
                    if (game_list[g][0].lower().strip() == team.lower().strip()) or (game_list[g][2].lower().strip() == team.lower().strip()):
                        embed.add_field(name=("**"+game_list[g][0]+"** " if int(game_list[g][1]) > int(game_list[g][3]) else game_list[g][0]+" ")+game_list[g][1]+" - "+("**"+game_list[g][2]+"** " if int(game_list[g][3]) > int(game_list[g][1]) else game_list[g][2]+" ")+game_list[g][3]+" *"+game_list[g][4]+"*",value='\u200b',inline=False)
                        if not game_list[g][4][1].isdigit():
                            embed.add_field(name="http://www.espn.com/"+league+"/boxscore?gameId="+g,value='\u200b',inline=False)
                        respond = True
                        break
            if respond:
                return embed
            else:
                return None

        async def get_scores(league):
            scores = {}
            STRIP = "()1234567890 "
            try:
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
                sys.exit(0)
                
        response = await get_game(team, league, await get_scores(league))
        if (response != None):
            await ctx.send(embed=response)
        else:
            await ctx.send("Something went wrong. Please try again.")
            await ctx.send_command_help(ctx.command)
