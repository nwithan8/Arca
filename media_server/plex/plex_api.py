from plexapi.server import PlexServer
from collections import defaultdict
import os
import re
import json
import requests
from media_server.plex import settings as settings
from os.path import exists
import xml.etree.ElementTree as ET
from helper.encryption import Encryption

plex = PlexServer(settings.PLEX_SERVER_URL[0], settings.PLEX_SERVER_TOKEN[0])
auth_header = "{'X-Plex-Token': '" + settings.PLEX_SERVER_TOKEN[0] + "'}"
cloud_key = None

crypt = Encryption('{}/credskey.txt'.format(settings.CREDENTIALS_FOLDER))

shows = defaultdict(list)
movies = defaultdict(list)

if settings.USE_OMBI:
    OMBI_URL = '{}/api/v1/'.format(settings.OMBI_URL)
    ombi_import = '{}Job/plexuserimporter'.format(OMBI_URL)
    ombi_users = '{}Identity/Users'.format(OMBI_URL)
    ombi_delete = '{}Identity/'.format(OMBI_URL)
    ombi_movie_count = '{}Request/movie/total'.format(OMBI_URL)
    ombi_movie_id = '{}Request/movie/1/'.format(OMBI_URL)
    ombi_approve_movie = '{}Request/movie/approve'.format(OMBI_URL)
    ombi_tv_count = '{}Request/tv/total'.format(OMBI_URL)
    ombi_tv_id = '{}Request/tv/1/'.format(OMBI_URL)
    ombi_approve_tv = '{}Request/tv/approve'.format(OMBI_URL)
    approve_header = {'ApiKey': settings.OMBI_API_KEY, 'accept': 'application/json',
                      'Content-Type': 'application/json-patch+json'}
    ombi_headers = {'ApiKey': settings.OMBI_API_KEY}


def t_request(cmd, params=None, serverNumber=None):
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
    r = requests.get('{}/library/metadata/{}?X-Plex-Token={}'.format(settings.PLEX_SERVER_URL[0], str(ratingKey),
                                                                     settings.PLEX_SERVER_TOKEN[0])).content
    tree = ET.fromstring(r)
    return tree.get('librarySectionID'), tree[0].get('title')


def getRatingKey(url):
    return str(re.search('metadata%2F(\d*)', url).group(1))


def getUrl(text):
    pattern = '{}\S*'.format(settings.PLEX_SERVER_URL[0].replace('.', '\.'))
    return str(re.search(pattern, text).group(0))


def checkPlaylist(playlistName):
    for playlist in plex.playlists():
        if playlist.title == playlistName:
            return playlist
    return None


def urlInMessage(message):
    if settings.PLEX_SERVER_ID[0] in message.content and 'metadata%2F' in message.content:
        return getUrl(message.content)
    if message.embeds:
        for embed in message.embeds:
            if settings.PLEX_SERVER_ID[0] in embed.title and 'metadata%2F' in embed.title:
                return getUrl(embed.title)
            elif settings.PLEX_SERVER_ID[0] in embed.description and 'metadata%2F' in embed.description:
                return getUrl(embed.description)
            elif settings.PLEX_SERVER_ID[0] in embed.description and 'metadata%2F' in embed.url:
                return getUrl(embed.url)
        return None
    return None


def getSmallestServer():
    serverNumber = 0
    smallestCount = 100
    for i in len(0, settings.PLEX_SERVER_URL[0]):
        tempCount = countServerSubs(i)
        if tempCount < smallestCount:
            serverNumber = i
            smallestCount = tempCount
    return serverNumber


def countServerSubs(serverNumber=None):
    tempPlex = plex
    tempServerName = settings.PLEX_SERVER_NAME[0]
    tempServerAltName = settings.PLEX_SERVER_ALT_NAME[0]
    if serverNumber and serverNumber >= 0:
        tempPlex = PlexServer(settings.PLEX_SERVER_URL[serverNumber], settings.PLEX_SERVER_TOKEN[serverNumber])
        tempServerName = settings.PLEX_SERVER_NAME[serverNumber]
        tempServerAltName = settings.PLEX_SERVER_ALT_NAME[serverNumber]
    count = 0
    for u in tempPlex.myPlexAccount().users():
        for s in u.servers:
            if s.name == tempServerName or s.name == tempServerAltName:
                count += 1
    return count


def getPlexFriends(serverNumber=None):
    """
    # Returns all usernames of Plex Friends (access in + access out)
    (lowercase for comparison)
    """
    if settings.MULTI_PLEX:
        if serverNumber:  # from a specific server
            tempPlex = PlexServer(settings.PLEX_SERVER_URL[serverNumber], settings.PLEX_SERVER_TOKEN[serverNumber])
            return [u.username.lower() for u in tempPlex.myPlexAccount().users()]
        else:  # from all servers
            users = []
            for i in range(len(settings.PLEX_SERVER_URL)):
                tempPlex = PlexServer(settings.PLEX_SERVER_URL[i], settings.PLEX_SERVER_TOKEN[i])
                for u in tempPlex.myPlexAccount().users():
                    users.append(u.username.lower())
            return users
    else:  # from the one server
        tempPlex = PlexServer(settings.PLEX_SERVER_URL[0], settings.PLEX_SERVER_TOKEN[0])
        return [u.username.lower() for u in tempPlex.myPlexAccount().users()]


def add_to_tautulli(plexname, serverNumber=None):
    if settings.USE_TAUTULLI:
        return t_request("refresh_users_list", None, serverNumber)
    return None


def delete_from_tautulli(plexname, serverNumber=None):
    if settings.USE_TAUTULLI:
        return t_request("delete_user", "user_id=" + str(plexname), serverNumber)
    return None


def add_to_ombi():
    if settings.USE_OMBI:
        return requests.post(ombi_import, headers=ombi_headers)
    return None


def delete_from_ombi(plexname):
    if settings.USE_OMBI:
        data = requests.get(ombi_users, headers=ombi_headers).json()
        uid = ""
        for i in data:
            if i['userName'].lower() == plexname:
                uid = i['id']
        to_delete = str(ombi_delete) + str(uid)
        return requests.delete(to_delete, headers=ombi_headers)
    return None


def get(hdr, endpoint, data=None):
    """ Returns JSON """
    hdr = {'accept': 'application/json', **hdr}
    res = requests.get('{}{}'.format(settings.PLEX_SERVER_URL[0], endpoint), headers=hdr, data=json.dumps(data)).json()
    return res


def post(hdr, endpoint, data=None):
    """ Returns response """
    hdr = {'accept': 'application/json', **hdr}
    res = requests.post('{}{}'.format(settings.PLEX_SERVER_URL[0], endpoint), headers=hdr, data=json.dumps(data))
    return res


def delete(hdr, endpoint, data=None):
    """ Returns response """
    hdr = {'accept': 'application/json', **hdr}
    res = requests.delete('{}{}'.format(settings.PLEX_SERVER_URL[0], endpoint), headers=hdr, data=json.dumps(data))
    return res


def get_cloud_key():
    global cloud_key
    if not cloud_key:
        data = get(hdr=auth_header, endpoint='/tv.plex.providers.epg.cloud')
        if data:
            cloud_key = data.get('MediaContainer').get('Directory')[1].get('title')
        else:
            return None
    return cloud_key


def get_live_tv_dvrs():
    data = get(hdr=auth_header, endpoint='/livetv/dvrs')
    if data:
        return data.get('MediaContainer').get('Dvr')
    return None


def get_live_tv_sessions():
    data = get(hdr=auth_header, endpoint='/livetv/sessions')
    if data:
        return data.get('MediaContainer')
    return None


def get_hubs(identifier=None):
    data = get(hdr=auth_header, endpoint='/{}/hubs/discover'.format(get_cloud_key()))
    if data:
        if identifier:
            for hub in data['MediaContainer']['Hub']:
                if hub['title'] == identifier:
                    return hub
            return None
        return data
    return None


def get_dvr_schedule():
    data = get(hdr=auth_header, endpoint='/media/subscriptions/scheduled')
    if data:
        return data.get('MediaContainer')
    return None


def get_dvr_items():
    data = get(hdr=auth_header, endpoint='/media/subscriptions')
    if data:
        return data.get('MediaContainer')
    return None


def delete_dvr_item(itemID):
    data = delete(hdr=auth_header, endpoint='/media/subscription/{}'.format(itemID))
    if str(data.status_code).startswith('2'):
        return True
    return False


def get_homepage_items():
    data = get(hdr=auth_header, endpoint='/hubs')
    if data:
        return data.get('MediaContainer').get('Hubs')
    return None
