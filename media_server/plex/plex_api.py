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
auth_header = {'X-Plex-Token': settings.PLEX_SERVER_TOKEN[0]}
cloud_key = None

crypt = Encryption(key_file='{}/credskey.txt'.format(settings.CREDENTIALS_FOLDER))

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


class Channel:
    def __init__(self, data):
        self.data = data
        self.deviceId = data.get('deviceIdentifier')
        self.enabled = data.get('enabled')
        self.lineupId = data.get('lineupIdentifier')


class Setting:
    def __init__(self, data):
        self.data = data
        self.id = data.get('id')
        self.label = data.get('label')
        self.summary = data.get('summary')
        self.type = data.get('type')
        self.default = data.get('default')
        self.value = data.get('value')
        self.hidden = data.get('hidden')
        self.advanced = data.get('advanced')
        self.group = data.get('group')
        self.enumValues = data.get('enumValues')


class Device:
    def __init__(self, data):
        self.data = data
        self.parentID = data.get('parentID')
        self.key = data.get('key')
        self.uuid = data.get('uuid')
        self.uri = data.get('uri')
        self.protocol = data.get('protocol')
        self.status = data.get('status')
        self.state = data.get('state')
        self.lastSeen = data.get('lastSeenAt')
        self.make = data.get('make')
        self.model = data.get('model')
        self.modelNumber = data.get('modelNumber')
        self.source = data.get('source')
        self.sources = data.get('sources')
        self.thumb = data.get('thumb')
        self.tuners = data.get('tuners')
        if data.get('Channels'):
            self.channels = [Channel(channel) for channel in data.get('Channels')]
        if data.get('Setting'):
            self.settings = [Setting(setting) for setting in data.get('Setting')]


class DVR:
    def __init__(self, data):
        self.data = data
        self.key = data.get('key')
        self.uuid = data.get('uuid')
        self.language = data.get('language')
        self.lineupURL = data.get('lineup')
        self.title = data.get('lineupTitle')
        self.country = data.get('country')
        self.refreshTime = data.get('refreshedAt')
        self.epgIdentifier = data.get('epgIdentifier')
        self.device = [Device(device) for device in data.get('Device')]


def get_live_tv_dvrs():
    data = get(hdr=auth_header, endpoint='/livetv/dvrs')
    if data:
        if data.get('MediaContainer').get('Dvr'):
            return [DVR(item) for item in data.get('MediaContainer').get('Dvr')]
    return None


class TVSession:
    def __init__(self, data):
        self.data = data
        self.ratingKey = data.get('ratingKey')
        self.guid = data.get('guid')
        self.type = data.get('type')
        self.title = data.get('title')
        self.summary = data.get('title')
        self.ratingCount = data.get('ratingCount')
        self.year = data.get('year')
        self.added = data.get('addedAt')
        self.genuineMediaAnalysis = data.get('genuineMediaAnalysis')
        self.grandparentThumb = data.get('grandparentThumb')
        self.grandparentTitle = data.get('grandparentTitle')
        self.key = data.get('key')
        self.live = data.get('live')
        self.parentIndex = data.get('parentIndex')
        self.media = [MediaItem(item) for item in data.get('Media')]


def get_live_tv_sessions():
    data = get(hdr=auth_header, endpoint='/livetv/sessions')
    if data:
        if data.get('MediaContainer').get('Metadata'):
            return [TVSession(item) for item in data.get('MediaContainer').get('Metadata')]
    return None


class MediaFile:
    def __init__(self, data):
        self.data = data
        self.id = data.get('id')
        self.duration = data.get('duration')
        self.audioChannels = data.get('audioChannels')
        self.videoResolution = data.get('videoResolution')
        self.channelCallSign = data.get('channelCallSign')
        self.channelIdentifier = data.get('channelIdentifier')
        self.channelThumb = data.get('channelThumb')
        self.channelTitle = data.get('channelTitle')
        self.protocol = data.get('protocol')
        self.begins = data.get('beginsAt')
        self.ends = data.get('endsAt')
        self.onAir = data.get('onAir')
        self.channelID = data.get('channelID')
        self.origin = data.get('origin')
        self.uuid = data.get('uuid')
        self.container = data.get('container')
        self.startOffsetSeconds = data.get('startOffsetSeconds')
        self.endOffsetSeconds = data.get('endOffsetSeconds')
        self.premiere = data.get('premiere')


class MediaItem:
    def __init__(self, data):
        self.data = data
        self.ratingKey = data.get('ratingKey')
        self.key = data.get('key')
        self.skipParent = data.get('skipParent')
        self.guid = data.get('guid')
        self.parentGuid = data.get('parentGuid')
        self.grandparentGuid = data.get('grandparentGuid')
        self.type = data.get('type')
        self.title = data.get('title')
        self.grandparentKey = data.get('grandparentKey')
        self.grandparentTitle = data.get('grandparentTitle')
        self.parentTitle = data.get('parentTitle')
        self.summary = data.get('summary')
        self.parentIndex = data.get('parentIndex')
        self.year = data.get('year')
        self.grandparentThumb = data.get('grandparentThumb')
        self.duration = data.get('duration')
        self.originallyAvailable = data.get('originallyAvailableAt')
        self.added = data.get('addedAt')
        self.onAir = data.get('onAir')
        if data.get('Media'):
            self.media = [MediaFile(item) for item in data.get('Media')]
        if data.get('Genre'):
            self.genres = [Genre(item) for item in data.get('Genre')]


class Genre:
    def __init__(self, data):
        self.data = data
        self.filter = data.get('filter')
        self.id = data.get('id')
        self.tag = data.get('tag')


class Hub:
    def __init__(self, data):
        self.data = data
        self.key = data.get('hubKey')
        self.title = data.get('title')
        self.type = data.get('type')
        self.identifier = data.get('hubIdentifier')
        self.context = data.get('context')
        self.size = data.get('size')
        self.more = data.get('more')
        self.promoted = data.get('promoted')
        if data.get('Metadata'):
            self.items = [MediaItem(item) for item in self.data.get('Metadata')]


def get_hubs(identifier=None):
    data = get(hdr=auth_header, endpoint='/{}/hubs/discover'.format(get_cloud_key()))
    if data:
        if identifier:
            for hub in data['MediaContainer']['Hub']:
                if hub['title'] == identifier:
                    return Hub(hub)
            return None
        return [Hub(hub) for hub in data['MediaContainer']['Hub']]
    return None


class DVRSchedule:
    def __init__(self, data):
        self.data = data
        self.count = data.get('size')
        if data.get('MediaGrabOperation'):
            self.items = [DVRItem(item) for item in data.get('MediaGrabOperation')]


class DVRItem:
    def __init__(self, data):
        self.data = data
        self.type = data.get('type')
        self.targetLibrarySectionID = data.get('targetLibrarySectionID')
        self.created = data.get('createdAt')
        self.title = data.get('title')
        self.mediaSubscriptionID = data.get('mediaSubscriptionID')
        self.mediaIndex = data.get('mediaIndex')
        self.key = data.get('key')
        self.grabberIdentifier = data.get('grabberIdentifier')
        self.grabberProtocol = data.get('grabberProtocol')
        self.deviceID = data.get('deviceID')
        self.status = data.get('status')
        self.provider = data.get('provider')
        if data.get('Video'):
            self.video = Video(data.get('Video'))


class Video:
    def __init__(self, data):
        self.data = data
        self.added = data.get('addedAt')
        self.duration = data.get('duration')
        self.grandparentGuid = data.get('grandparentGuid')
        self.grandparentKey = data.get('grandparentKey')
        self.grandparentRatingKey = data.get('grandparentRatingKey')
        self.grandparentThumb = data.get('grandparentThumb')
        self.grandparentTitle = data.get('grandparentTitle')
        self.guid = data.get('guid')
        self.key = data.get('key')
        self.librarySectionID = data.get('librarySectionID')
        self.librarySectionKey = data.get('librarySectionKey')
        self.librarySectionTitle = data.get('librarySectionTitle')
        self.mediaProviderID = data.get('mediaProviderID')
        self.originallyAvailable = data.get('originallyAvailable')
        self.parentGuid = data.get('parentGuid')
        self.parentIndex = data.get('parentIndex')
        self.parentTitle = data.get('parentTitle')
        self.ratingKey = data.get('ratingKey')
        self.skipParent = data.get('skipParent')
        self.subscriptionID = data.get('subscriptionID')
        self.subscriptionType = data.get('subscriptionType')
        self.summary = data.get('summary')
        self.title = data.get('title')
        self.type = data.get('type')
        self.year = data.get('year')
        if data.get('Media'):
            self.items = [MediaFile(item) for item in data.get('Media')]
        if data.get('Genre'):
            self.genres = [Genre(item) for item in data.get('Genre')]


def get_dvr_schedule():
    data = get(hdr=auth_header, endpoint='/media/subscriptions/scheduled')
    if data:
        return DVRSchedule(data.get('MediaContainer'))
    return None


def get_dvr_items():
    data = get(hdr=auth_header, endpoint='/media/subscriptions')
    if data:
        return [DVRItem(item) for item in data.get('MediaContainer').get('MediaSubscription')]
    return None


def delete_dvr_item(itemID):
    data = delete(hdr=auth_header, endpoint='/media/subscription/{}'.format(itemID))
    if str(data.status_code).startswith('2'):
        return True
    return False


def get_homepage_items():
    data = get(hdr=auth_header, endpoint='/hubs')
    if data:
        return [Hub(item) for item in data.get('MediaContainer').get('Hub')]
    return None
