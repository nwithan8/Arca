import discord
import requests
import json
from imdbpie import Imdb, ImdbFacade
import random
from progress.bar import Bar
from media_server.plex import plex_api as px
from media_server.plex import settings as settings
from urllib.parse import quote

imdbf = ImdbFacade()
imdb = Imdb()

libraries = {}
for name, numbers in settings.PLEX_RECS_LIBRARIES.items():
    libraries[name] = [numbers, []]

owner_players = []
emoji_numbers = [u"1\u20e3", u"2\u20e3", u"3\u20e3", u"4\u20e3", u"5\u20e3"]


# Currently only support for one Plex Server & one Tautulli instance

def request(cmd, params):
    url = '{base}/api/v2?apikey={key}&cmd={cmd}'.format(base=settings.TAUTULLI_URL[0],
                                                        key=settings.TAUTULLI_API_KEY[0], cmd=cmd)
    if params:
        url = '{base}/api/v2?apikey={key}&{params}&cmd={cmd}'.format(base=settings.TAUTULLI_URL[0],
                                                                     key=settings.TAUTULLI_API_KEY[0],
                                                                     params=params, cmd=cmd)
    return json.loads(requests.get(url).text)


def cleanLibraries():
    global libraries
    for groupName, items in libraries.items():
        libraries[groupName][1] = []


class SmallMediaItem:
    def __init__(self, title, year, ratingKey, librarySectionID, mediaType):
        self.title = title
        self.year = year
        self.ratingKey = ratingKey
        self.librarySectionID = librarySectionID
        self.type = mediaType


def makeLibrary(libraryName):
    try:
        global libraries
        if not libraries[libraryName][1]:
            for libraryNumber in libraries[libraryName][0]:
                json_data = request("get_library", "section_id={}".format(libraryNumber))
                count = json_data['response']['data']['count']
                bar = Bar('Loading {} (Library section {})'.format(libraryName, libraryNumber), max=int(count))
                librarySection = px.plex.library.sectionByID(str(libraryNumber))
                for item in librarySection.all():
                    libraries[libraryName][1].append(
                        SmallMediaItem(item.title, (None if librarySection.type == 'artist' else item.year),
                                       item.ratingKey, item.librarySectionID, item.type))
                    bar.next()
                bar.finish()
            return True
        return False
    except Exception as e:
        print('Error in makeLibrary: {}'.format(e))
        return False


def getPoster(embed, title):
    try:
        embed.set_image(url=str(imdbf.get_title(imdb.search_for_title(title)[0]['imdb_id']).image.url))
        return embed
    except Exception as e:
        print("Error in getPoster: {}".format(e))
        return embed


def makeEmbed(mediaItem):
    embed = discord.Embed(title=mediaItem.title,
                          url='{base}/web/index.html#!/server/{id}/details?key=%2Flibrary%2Fmetadata%2F{ratingKey}'.format(
                              base=settings.PLEX_SERVER_URL[0], id=settings.PLEX_SERVER_ID[0],
                              ratingKey=mediaItem.ratingKey,
                              description="Watch it on {}".format(settings.PLEX_SERVER_NAME[0])))
    if mediaItem.type not in ['artist', 'album', 'track']:
        embed = getPoster(embed, mediaItem.title)
    return embed


def getHistory(username, sectionIDs):
    try:
        user_id = None
        users = request('get_users', None)
        for user in users['response']['data']:
            if user['username'] == username:
                user_id = user['user_id']
                break
        if not user_id:
            print("I couldn't find that username. Please check and try again.")
            return "Error"
        watched_titles = []
        for sectionID in sectionIDs:
            history = request('get_history', 'section_id={}&user_id={}&length=10000'.format(str(sectionID), user_id))
            for watched_item in history['response']['data']['data']:
                watched_titles.append(watched_item['full_title'])
        return watched_titles
    except Exception as e:
        print("Error in getHistory: {}".format(e))
        return "Error"


def pickUnwatched(history, mediaList):
    """
    Keep picking until something is unwatched
    :param history:
    :param mediaList: Movies list, Shows list or Artists list
    :return: SmallMediaItem object
    """
    if history == "Error":
        return False
    if len(history) >= mediaList:
        return 'All'
    choice = random.choice(mediaList)
    if choice.title in history:
        return pickUnwatched(history, mediaList)
    return choice


def pickRandom(aList):
    return random.choice(aList)


def findRec(username, mediaType, unwatched=False):
    """

    :param username:
    :param unwatched:
    :param mediaType: 'movie', 'show' or 'artist'
    :return:
    """
    try:
        if unwatched:
            return pickUnwatched(history=getHistory(username, libraries[mediaType][0]),
                                 mediaList=libraries[mediaType][1])
        else:
            return pickRandom(libraries[mediaType][1])
    except Exception as e:
        print("Error in findRec: {}".format(e))
        return False


def makeRecommendation(mediaType, unwatched, PlexUsername):
    if unwatched:
        if not PlexUsername:
            return "Please include a Plex username"
        recommendation = findRec(PlexUsername, mediaType, True)
        if not recommendation:
            return "I couldn't find that Plex username"
        if recommendation == 'All':
            return "You've already played everything in that section!"
    else:
        recommendation = findRec(None, mediaType, False)
    embed = makeEmbed(recommendation)
    return "How about {}?{}".format(recommendation.title, ('\nClick 🎞️ to watch a trailer.' if recommendation.type not in ['artist', 'album', 'track'] else "")), embed, recommendation


def getPlayers(mediaType):
    global owner_players
    owner_players = []
    players = px.plex.clients()
    if not players:
        return False, 0
    num = 0
    players_list = ""
    for player in players[:5]:
        num = num + 1
        players_list = '{}\n{}:{}'.format(players_list, num, player.title)
        owner_players.append(player)
    return '{}\nReact with which player you want to start this {} on.'.format(players_list, mediaType), num


def getFullMediaItem(mediaItem):
    librarySection = px.plex.library.sectionByID(mediaItem.librarySectionID)
    for item in librarySection.search(title=mediaItem.title, year=[mediaItem.year]):
        if item.ratingKey == mediaItem.ratingKey:
            return item
    return None


def playMedia(playerNumber, mediaItem):
    owner_players[playerNumber].goToMedia(mediaItem)


def getTrailerURL(mediaItem):
    url = 'https://www.googleapis.com/youtube/v3/search?q={query}&key={key}&part=snippet&type=video'.format(
        query=quote('{} {} trailer'.format(mediaItem.title, ('movie' if mediaItem.type == 'movie' else 'tv show'))),
        key=settings.YOUTUBE_API_KEY
    )
    result = requests.get(url).json()['items'][0]
    if result:
        return 'https://www.youtube.com/watch?v={}'.format(result['id']['videoId'])
    return "Sorry, I couldn't grab the trailer."
