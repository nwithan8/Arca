import discord
from plexapi.server import PlexServer
from collections import defaultdict
import os
import re
import json
import requests
import random
from progress.bar import Bar
import plex.settings as settings
from os.path import exists
from imdbpie import Imdb
from imdbpie import ImdbFacade
import xml.etree.ElementTree as ET
from plex.encryption import Encryption

plex = PlexServer(settings.PLEX_SERVER_URL[0], settings.PLEX_SERVER_TOKEN[0])

crypt = Encryption('{}/credskey.txt'.format(settings.CREDENTIALS_FOLDER))

imdbf = ImdbFacade()
imdb = Imdb()

shows = defaultdict(list)
movies = defaultdict(list)


def t_request(cmd, params, serverNumber=None):
    if params:
        return json.loads(requests.get(
            "{}/api/v2?apikey={}&{}&cmd={}".format(
                (settings.TAUTULLI_URL[serverNumber] if serverNumber is not None else settings.TAUTULLI_URL[0]),
                (settings.TAUTULLI_API_KEY[serverNumber] if serverNumber is not None else settings.TAUTULLI_API_KEY[0]),
                params,
                cmd
            )
        ).text)
    return json.loads(requests.get(
        "{}/api/v2?apikey={}&cmd={}".format(
            (settings.TAUTULLI_URL[serverNumber] if serverNumber is not None else settings.TAUTULLI_URL[0]),
            (settings.TAUTULLI_API_KEY[serverNumber] if serverNumber is not None else settings.TAUTULLI_API_KEY[0]),
            cmd
        )
    ).text)


def filesize(size):
    pf = ['Byte', 'Kilobyte', 'Megabyte', 'Gigabyte', 'Terabyte', 'Petabyte', 'Exabyte', 'Zettabyte', 'Yottabyte']
    i = 0
    while size > 1024:
        i += 1
        size /= 1024
    return "{:.2f}".format(size) + " " + pf[i] + ("s" if size != 1 else "")


def getLibraries():
    global shows, movies
    items = defaultdict(list)
    movies.clear()
    shows.clear()
    if not movies:
        media = plex.library.section(settings.MOVIE_LIBRARY_NAME)
        json_data = t_request('get_library', 'section_id=' + str(settings.MOVIE_LIBRARY))
        count = json_data['response']['data']['count']
        # bar = Bar('Loading movies', max=int(count))
        for results in media.search():
            movies['Results'].append([results.title, results.year])
            # bar.next()
        # bar.finish()
    if not shows:
        media = plex.library.section(settings.TV_SHOW_LIBRARY_NAME)
        json_data = t_request('get_library', 'section_id=' + str(settings.TV_LIBRARY))
        count = json_data['response']['data']['count']
        # bar = Bar('Loading TV shows', max=int(count))
        for results in media.search():
            shows['Results'].append([results.title, results.year])
            # bar.next()
        # bar.finish()


def getposter(att, title):
    try:
        att.set_image(url=str(imdbf.get_title(imdb.search_for_title(title)[0]['imdb_id']).image.url))
        return att
    except IndexError as e:
        return att


def findrec(library: int):
    suggestion = 0
    if library == settings.MOVIE_LIBRARY:
        rand = random.choice(movies['Results'])
        try:
            suggestion = plex.library.section(settings.MOVIE_LIBRARY_NAME).search(title=rand[0], year=rand[1])[0]
        except:
            return "Oops, something went wrong. Want to try again?", None, None, None
    else:
        rand = random.choice(shows['Results'])
        try:
            suggestion = plex.library.section(settings.TV_SHOW_LIBRARY_NAME).search(title=rand[0], year=rand[1])[0]
        except:
            return "Oops, something went wrong. Want to try again?", None, None, None
    att = discord.Embed(title=str(suggestion.title),
                        url="https://app.plex.tv/desktop#!/server/" + settings.PLEX_SERVER_ID + "/details?key=%2Flibrary%2Fmetadata%2F" + str(
                            suggestion.ratingKey), description="Watch it on " + settings.PLEX_SERVER_NAME)
    att = getposter(att, str(suggestion.title))
    return "How about " + str(suggestion.title) + "?", att, suggestion


def unwatched(mediaType: str, library: int, username: str):
    library_name = ""
    if library == settings.MOVIE_LIBRARY:
        library_name = settings.MOVIE_LIBRARY_NAME
    else:
        library_name = settings.TV_SHOW_LIBRARY_NAME
    names = []
    ids = []
    for user in t_request("get_users", None)['response']['data']:
        names.append(user['username'])
        ids.append(user['user_id'])
    try:
        user_id = str(ids[names.index(username)])
    except:
        return "I couldn\'t find that username. Please check and try again.", None, None, None
    watched_titles = []
    for watched_item in \
            t_request("get_history", "user_id=" + str(user_id) + "&length=10000")['response']['data']['data']:
        watched_titles.append(watched_item["full_title"])
    unwatched_titles = []
    for media in (movies['Results'] if mediaType == "movie" else shows['Results']):
        if not media[0] in watched_titles:
            unwatched_titles.append(media)
    rand = random.choice(unwatched_titles)
    try:
        suggestion = plex.library.section(library_name).search(title=rand[0], year=rand[1])[0]
    except:
        return "Oops, something went wrong. Want to try again?", None, None, None
    att = discord.Embed(title=str(suggestion.title),
                        url="https://app.plex.tv/desktop#!/server/" + settings.PLEX_SERVER_ID + "/details?key=%2Flibrary%2Fmetadata%2F" + str(
                            suggestion.ratingKey), description="Watch it on " + settings.PLEX_SERVER_NAME)
    att = getposter(att, str(suggestion.title))
    return "How about " + str(suggestion.title) + "?", att, suggestion


def recommend(mediaType, recNew, username):
    library = 0
    if mediaType == "movie":
        library = settings.MOVIE_LIBRARY
    else:
        library = settings.TV_LIBRARY
    if recNew:
        return unwatched(mediaType, library, username)
    else:
        return findrec(library)


def getUserCreds(user_id):
    if exists('{}/{}.json'.format(settings.CREDENTIALS_FOLDER, str(user_id))):
        crypt.makeTemporaryFile('{}{}.json'.format(settings.CREDENTIALS_FOLDER, str(user_id)),
                                '{}/{}_temp.json'.format(settings.CREDENTIALS_FOLDER, str(user_id)))
        creds = crypt.decryptFile('{}/{}_temp.json'.format(settings.CREDENTIALS_FOLDER, str(user_id))).splitlines()
        os.remove('{}/{}_temp.json'.format(settings.CREDENTIALS_FOLDER, str(user_id)))
        return {'username': creds[0], 'password': creds[1]}


def saveUserCreds(user_id, username, password):
    text = '{}\n{}'.format(username, password)
    crypt.encryptFile(text, '{}/{}.json'.format(settings.CREDENTIALS_FOLDER, str(user_id)))


def getMediaItem(title, ratingKey=None, libraryID=None):
    library = plex.library
    if libraryID:
        library = library.sectionByID(str(libraryID))
    results = library.search(title=title)
    if results:
        if ratingKey:  # find exact match
            for item in results:
                if item.ratingKey == ratingKey:
                    return item
        return results[0]  # assume first result is correct
    return None


def getMediaInfo(ratingKey):
    r = requests.get('{}/library/metadata/{}?X-Plex-Token={}'.format(settings.PLEX_SERVER_URL, str(ratingKey),
                                                                     PLEX_SERVER_TOKEN)).content
    tree = ET.fromstring(r)
    return tree.get('librarySectionID'), tree[0].get('title')


def getRatingKey(url):
    return str(re.search('metadata%2F(\d*)', url).group(1))


def getUrl(text):
    pattern = '{}\S*'.format(settings.PLEX_SERVER_URL.replace('.', '\.'))
    return str(re.search(pattern, text).group(0))


def checkPlaylist(playlistName):
    for playlist in plex.playlists():
        if playlist.title == playlistName:
            return playlist
    return None


def urlInMessage(message):
    if settings.PLEX_SERVER_ID in message.content and 'metadata%2F' in message.content:
        return getUrl(message.content)
    if message.embeds:
        for embed in message.embeds:
            if settings.PLEX_SERVER_ID in embed.title and 'metadata%2F' in embed.title:
                return getUrl(embed.title)
            elif settings.PLEX_SERVER_ID in embed.description and 'metadata%2F' in embed.description:
                return getUrl(embed.description)
            elif settings.PLEX_SERVER_ID in embed.description and 'metadata%2F' in embed.url:
                return getUrl(embed.url)
        return None
    return None


def getSmallestServer():
    serverNumber = 0
    smallestCount = 100
    for i in len(0, settings.PLEX_SERVER_URL):
        tempCount = countServerSubs(i)
        if tempCount < smallestCount:
            serverNumber = i
            smallestCount = tempCount
    return serverNumber


def countServerSubs(serverNumber):
    tempPlex = plex
    tempServerName = settings.PLEX_SERVER_NAME
    tempServerAltName = settings.PLEX_SERVER_ALT_NAME
    if serverNumber >= 0:
        tempPlex = PlexServer(settings.PLEX_SERVER_URL[serverNumber], settings.PLEX_SERVER_TOKEN[serverNumber])
        tempServerName = settings.PLEX_SERVER_NAME[serverNumber]
        tempServerAltName = settings.PLEX_SERVER_ALT_NAME[serverNumber]
    count = 0
    for u in tempPlex.myPlexAccount().users():
        for s in u.servers:
            if s.name == tempServerName or s.name == tempServerAltName:
                count += 1
    return count


def getPlexUsers(serverNumber=None):
    """
    Returns all usernames (lowercase for comparison)
    """
    users = []
    tempPlex = plex
    tempServerName = settings.PLEX_SERVER_NAME
    tempServerAltName = settings.PLEX_SERVER_ALT_NAME
    if settings.MULTI_PLEX:
        if serverNumber:  # from specific server
            tempPlex = PlexServer(settings.PLEX_SERVER_URL[serverNumber], settings.PLEX_SERVER_TOKEN[serverNumber])
            tempServerName = settings.PLEX_SERVER_NAME[serverNumber]
            tempServerAltName = settings.PLEX_SERVER_ALT_NAME[serverNumber]
            for u in tempPlex.myPlexAccount().users():
                for s in u.servers:
                    if s.name == tempServerName or s.name == tempServerAltName:
                        users.append(u.username.lower())
        else:  # from all servers
            for serverNumber in range(len(settings.PLEX_SERVER_URL)):
                tempPlex = PlexServer(settings.PLEX_SERVER_URL[serverNumber], settings.PLEX_SERVER_TOKEN[serverNumber])
                tempServerName = settings.PLEX_SERVER_NAME[serverNumber]
                tempServerAltName = settings.PLEX_SERVER_ALT_NAME[serverNumber]
                for u in tempPlex.myPlexAccount().users():
                    for s in u.servers:
                        if s.name == tempServerName or s.name == tempServerAltName:
                            users.append(u.username.lower())
    else:  # from the single server
        for u in tempPlex.myPlexAccount().users():
            for s in u.servers:
                if s.name == tempServerName or s.name == tempServerAltName:
                    users.append(u.username.lower())
    return users
