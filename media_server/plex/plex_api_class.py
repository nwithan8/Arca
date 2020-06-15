from plexapi.server import PlexServer
from collections import defaultdict
import os
import re
import json
import requests
# from media_server.plex import settings as settings
from helper.media_server_classes import PlexConfig
from os.path import exists
import xml.etree.ElementTree as ET
import helper.helper_functions as helper_functions
from helper.encryption import Encryption


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


class PlexAPI:
    def __init__(self):
        self.settings = None
        self.plex = None
        self.auth_header = None
        self.cloud_key = None
        self.crypt = None
        self.shows = None
        self.movies = None
        self.all_movie_ratings = None
        self.all_tv_ratings = None
        self.OMBI_URL = None
        self.ombi_import = None
        self.ombi_users = None
        self.ombi_delete = None
        self.ombi_movie_count = None
        self.ombi_movie_id = None
        self.ombi_approve_movie = None
        self.ombi_tv_count = None
        self.ombi_tv_id = None
        self.ombi_approve_tv = None
        self.approve_header = None
        self.ombi_headers = None

    def change_settings_file(self, new_settings):
        self.settings = new_settings
        self.plex = PlexServer(self.settings.PLEX_SERVER_URLS[0], self.settings.PLEX_SERVER_TOKENS[0])
        self.auth_header = {'X-Plex-Token': self.settings.PLEX_SERVER_TOKENS[0]}
        self.cloud_key = None

        crypt = Encryption(key_file='{}/credskey.txt'.format(self.settings.CREDENTIALS_FOLDER))

        shows = defaultdict(list)
        movies = defaultdict(list)

        all_movie_ratings = ['12', 'Approved', 'Passed', 'G', 'GP', 'PG', 'PG-13', 'M', 'R', 'NC-17', 'Unrated',
                             'Not Rated',
                             'NR', 'None']
        all_tv_ratings = ['TV-Y', 'TV-Y7', 'TV-G', 'TV-PG', 'TV-14', 'TV-MA', 'NR']

        if self.settings.USE_OMBI:
            OMBI_URL = '{}/api/v1/'.format(self.settings.OMBI_URL)
            ombi_import = '{}Job/plexuserimporter'.format(OMBI_URL)
            ombi_users = '{}Identity/Users'.format(OMBI_URL)
            ombi_delete = '{}Identity/'.format(OMBI_URL)
            ombi_movie_count = '{}Request/movie/total'.format(OMBI_URL)
            ombi_movie_id = '{}Request/movie/1/'.format(OMBI_URL)
            ombi_approve_movie = '{}Request/movie/approve'.format(OMBI_URL)
            ombi_tv_count = '{}Request/tv/total'.format(OMBI_URL)
            ombi_tv_id = '{}Request/tv/1/'.format(OMBI_URL)
            ombi_approve_tv = '{}Request/tv/approve'.format(OMBI_URL)
            approve_header = {'ApiKey': self.settings.OMBI_API_KEY, 'accept': 'application/json',
                              'Content-Type': 'application/json-patch+json'}
            ombi_headers = {'ApiKey': self.settings.OMBI_API_KEY}

    def t_request(self, cmd, params=None, serverNumber=None):
        if params:
            return json.loads(requests.get(
                "{}/api/v2?apikey={}&{}&cmd={}".format(
                    (self.settings.TAUTULLI_URLS[serverNumber] if serverNumber is not None else
                     self.settings.TAUTULLI_URLS[0]),
                    (self.settings.TAUTULLI_API_KEYS[serverNumber] if serverNumber is not None else
                     self.settings.TAUTULLI_API_KEY[
                         0]),
                    params,
                    cmd
                )
            ).text)
        return json.loads(requests.get(
            "{}/api/v2?apikey={}&cmd={}".format(
                (self.settings.TAUTULLI_URLS[serverNumber] if serverNumber is not None else self.settings.TAUTULLI_URLS[
                    0]),
                (self.settings.TAUTULLI_API_KEYS[serverNumber] if serverNumber is not None else
                 self.settings.TAUTULLI_API_KEY[0]),
                cmd
            )
        ).text)

    def getUserCreds(self, user_id):
        if exists('{}/{}.json'.format(self.settings.CREDENTIALS_FOLDER, str(user_id))):
            self.crypt.makeTemporaryFile('{}{}.json'.format(self.settings.CREDENTIALS_FOLDER, str(user_id)),
                                         '{}/{}_temp.json'.format(self.settings.CREDENTIALS_FOLDER, str(user_id)))
            creds = self.crypt.decryptFile(
                '{}/{}_temp.json'.format(self.settings.CREDENTIALS_FOLDER, str(user_id))).splitlines()
            os.remove('{}/{}_temp.json'.format(self.settings.CREDENTIALS_FOLDER, str(user_id)))
            return {'username': creds[0], 'password': creds[1]}

    def saveUserCreds(self, user_id, username, password):
        text = '{}\n{}'.format(username, password)
        self.crypt.encryptFile(text, '{}/{}.json'.format(self.settings.CREDENTIALS_FOLDER, str(user_id)))

    def getMediaItem(self, title, ratingKey=None, libraryID=None):
        library = self.plex.library
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

    def getMediaInfo(self, ratingKey):
        r = requests.get(
            '{}/library/metadata/{}?X-Plex-Token={}'.format(self.settings.PLEX_SERVER_URLS[0], str(ratingKey),
                                                            self.settings.PLEX_SERVER_TOKENS[0])).content
        tree = ET.fromstring(r)
        return tree.get('librarySectionID'), tree[0].get('title')

    def getRatingKey(self, url):
        return str(re.search('metadata%2F(\d*)', url).group(1))

    def getUrl(self, text):
        pattern = '{}\S*'.format(self.settings.PLEX_SERVER_URLS[0].replace('.', '\.'))
        return str(re.search(pattern, text).group(0))

    def getTempServer(self, server_number=None):
        if server_number:
            return PlexServer(self.settings.PLEX_SERVER_URLS[server_number],
                              self.settings.PLEX_SERVER_TOKENS[server_number])
        return self.plex

    def checkPlaylist(self, playlistName):
        for playlist in self.plex.playlists():
            if playlist.title == playlistName:
                return playlist
        return None

    def urlInMessage(self, message):
        if self.settings.PLEX_SERVER_IDS[0] in message.content and 'metadata%2F' in message.content:
            return self.getUrl(message.content)
        if message.embeds:
            for embed in message.embeds:
                if self.settings.PLEX_SERVER_IDS[0] in embed.title and 'metadata%2F' in embed.title:
                    return self.getUrl(embed.title)
                elif self.settings.PLEX_SERVER_IDS[0] in embed.description and 'metadata%2F' in embed.description:
                    return self.getUrl(embed.description)
                elif self.settings.PLEX_SERVER_IDS[0] in embed.description and 'metadata%2F' in embed.url:
                    return self.getUrl(embed.url)
            return None
        return None

    def getSmallestServer(self):
        serverNumber = 0
        smallestCount = 100
        for i in range(0, len(self.settings.PLEX_SERVER_URLS)):
            tempCount = self.countServerSubs(i)
            if tempCount < smallestCount:
                serverNumber = i
                smallestCount = tempCount
        return serverNumber

    def countServerSubs(self, serverNumber=None):
        tempPlex = self.plex
        tempServerName = self.settings.PLEX_SERVER_NAMES[0]
        tempServerAltName = self.settings.PLEX_SERVER_ALT_NAMES[0]
        if serverNumber and serverNumber >= 0:
            tempPlex = PlexServer(self.settings.PLEX_SERVER_URLS[serverNumber],
                                  self.settings.PLEX_SERVER_TOKENS[serverNumber])
            tempServerName = self.settings.PLEX_SERVER_NAMES[serverNumber]
            tempServerAltName = self.settings.PLEX_SERVER_ALT_NAMES[serverNumber]
        count = 0
        for u in tempPlex.myPlexAccount().users():
            for s in u.servers:
                if s.name == tempServerName or s.name == tempServerAltName:
                    count += 1
        return count

    def getServerUsers(self, server):
        try:
            return server.myPlexAccount().users()
        except Exception as e:
            print(f"Error in getServerUsers: {e}")
        return []

    def getServerUser(self, server, plexname):
        try:
            return server.myPlexAccount().user(plexname)
        except Exception as e:
            print(f"Error in getServerUser: {e}")
        return None

    def getPlexFriends(self, serverNumber=None):
        """
        # Returns all Plex Friends (access in + access out)
        """
        try:
            if self.settings.MULTI_PLEX:
                if serverNumber:  # from a specific server
                    tempPlex = self.getTempServer(server_number=serverNumber)
                    return self.getServerUsers(server=tempPlex)
                else:  # from all servers
                    users = []
                    for i in range(len(self.settings.PLEX_SERVER_URLS)):
                        tempPlex = self.getTempServer(server_number=serverNumber)
                        for u in self.getServerUsers(server=tempPlex):
                            users.append(u)
                    return users
            else:  # from the one server
                tempPlex = self.getTempServer()
                return self.getServerUsers(server=tempPlex)
        except Exception as e:
            print(f"Error in getPlexFriends: {e}")
        return []

    def get_defined_libraries(self):
        names = [name for name in self.settings.PLEX_LIBRARIES.keys()]
        ids = []
        for _, vs in self.settings.PLEX_LIBRARIES.items():
            for v in vs:
                if v not in ids:
                    ids.append(str(v))
        return {'Names': names, 'IDs': ids}

    def get_plex_share(self, share_name_or_num):
        if not self.settings.PLEX_LIBRARIES:
            return False
        if helper_functions.is_positive_int(share_name_or_num):
            return [int(share_name_or_num)]
        else:
            for name, numbers in self.settings.PLEX_LIBRARIES.items():
                if name == share_name_or_num:
                    return numbers
            return False

    def get_plex_restrictions(self, plexname, server_number=None):
        try:
            target_user = None
            friends = self.getPlexFriends(
                serverNumber=server_number)  # rather than getServerUser because no need to specify which server if MULTI_PLEX
            if not friends:
                raise Exception("No users received in get_plex_restrictions function.")
            for user in friends:
                if user.username.lower() == plexname.lower():
                    target_user = user
                    break
            if not target_user:
                raise Exception(f"{plexname} not found in Plex Friends.")
            try:
                sections = target_user.server((self.settings.PLEX_SERVER_NAMES[server_number] if server_number else
                                               self.settings.PLEX_SERVER_NAMES[0])).sections()
            except:
                sections = target_user.server((self.settings.PLEX_SERVER_ALT_NAMES[server_number] if server_number else
                                               self.settings.PLEX_SERVER_ALT_NAMES[0])).sections()
            if not sections:
                raise Exception(f"Couldn't load sections for {plexname}.")
            details = {'allowSync': target_user.allowSync, 'filterMovies': target_user.filterMovies,
                       'filterShows': target_user.filterTelevision,
                       'sections': ([section.title for section in sections] if sections else [])}
            return details
        except Exception as e:
            print(f"Error in get_plex_restrictions: {e}")
        return None

    def add_to_plex(self, server, plexname):
        try:
            server.myPlexAccount().inviteFriend(user=plexname, server=server, sections=None, allowSync=False,
                                                allowCameraUpload=False, allowChannels=False, filterMovies=None,
                                                filterTelevision=None, filterMusic=None)
            return True
        except Exception as e:
            print(f"Error in add_to_plex: {e}")
        return False

    def update_plex_share(self, server, plexname, sections_to_share=[], rating_limit={}, allow_sync: bool = None):
        """

        :param server:
        :param plexname:
        :param sections_to_share:
        :param rating_limit: ex. {'Movie': 'PG-13', 'TV': 'TV-14'}
        :param allow_sync:
        :return:
        """
        try:
            # collect section names and numbers
            sections = []
            for section in sections_to_share:
                section_numbers = self.get_plex_share(section)
                if section_numbers:
                    for n in section_numbers:
                        sections.append(str(n))
            allowed_movie_ratings = []
            allowed_tv_ratings = []
            if rating_limit:
                # add max rating and all below it to allowed ratings
                # if non_existent rating is used as limit, all ratings will be added
                if rating_limit.get('Movie') and rating_limit.get('Movie') in self.all_movie_ratings:
                    for rating in self.all_movie_ratings:
                        allowed_movie_ratings.append(rating)
                        if rating == rating_limit.get('Movie'):
                            break
                if rating_limit.get('TV') and rating_limit.get('TV') in self.all_tv_ratings:
                    for rating in self.all_tv_ratings:
                        allowed_tv_ratings.append(rating)
                        if rating == rating_limit.get('TV'):
                            break
            server.myPlexAccount().updateFriend(user=plexname, server=server, sections=(sections if sections else None),
                                                removeSections=False, allowSync=allow_sync, allowCameraUpload=None,
                                                allowChannels=None,
                                                filterMovies=(
                                                    {
                                                        'contentRating': allowed_movie_ratings} if allowed_movie_ratings else None),
                                                filterTelevision=(
                                                    {
                                                        'contentRating': allowed_tv_ratings} if allowed_tv_ratings else None),
                                                filterMusic=None)
            return True
        except Exception as e:
            print(f"Error in update_plex_share: {e}")
        return False

    def delete_from_plex(self, server, plexname):
        try:
            server.myPlexAccount().removeFriend(user=plexname)
            return True
        except Exception as e:
            print(f"Error in delete_from_plex: {e}")
        return False

    def refresh_tautulli(self, serverNumber=None):
        if self.settings.USE_TAUTULLI:
            return self.t_request("refresh_users_list", None, serverNumber)
        return None

    def delete_from_tautulli(self, plexname, serverNumber=None):
        if self.settings.USE_TAUTULLI:
            return self.t_request("delete_user", "user_id=" + str(plexname), serverNumber)
        return None

    def refresh_ombi(self):
        if self.settings.USE_OMBI:
            return requests.post(self.ombi_import, headers=self.ombi_headers)
        return None

    def delete_from_ombi(self, plexname):
        if self.settings.USE_OMBI:
            data = requests.get(self.ombi_users, headers=self.ombi_headers).json()
            uid = ""
            for i in data:
                if i['userName'].lower() == plexname:
                    uid = i['id']
            to_delete = str(self.ombi_delete) + str(uid)
            return requests.delete(to_delete, headers=self.ombi_headers)
        return None

    def get(self, hdr, endpoint, data=None):
        """ Returns JSON """
        hdr = {'accept': 'application/json', **hdr}
        res = requests.get('{}{}'.format(self.settings.PLEX_SERVER_URLS[0], endpoint), headers=hdr,
                           data=json.dumps(data)).json()
        return res

    def post(self, hdr, endpoint, data=None):
        """ Returns response """
        hdr = {'accept': 'application/json', **hdr}
        res = requests.post('{}{}'.format(self.settings.PLEX_SERVER_URLS[0], endpoint), headers=hdr,
                            data=json.dumps(data))
        return res

    def delete(self, hdr, endpoint, data=None):
        """ Returns response """
        hdr = {'accept': 'application/json', **hdr}
        res = requests.delete('{}{}'.format(self.settings.PLEX_SERVER_URLS[0], endpoint), headers=hdr,
                              data=json.dumps(data))
        return res

    def get_cloud_key(self):
        global cloud_key
        if not cloud_key:
            data = self.get(hdr=self.auth_header, endpoint='/tv.plex.providers.epg.cloud')
            if data:
                cloud_key = data.get('MediaContainer').get('Directory')[1].get('title')
            else:
                return None
        return cloud_key

    def get_live_tv_dvrs(self):
        data = self.get(hdr=self.auth_header, endpoint='/livetv/dvrs')
        if data:
            if data.get('MediaContainer').get('Dvr'):
                return [DVR(item) for item in data.get('MediaContainer').get('Dvr')]
        return None

    def get_live_tv_sessions(self):
        data = self.get(hdr=self.auth_header, endpoint='/livetv/sessions')
        if data:
            if data.get('MediaContainer').get('Metadata'):
                return [TVSession(item) for item in data.get('MediaContainer').get('Metadata')]
        return None

    def get_hubs(self, identifier=None):
        data = self.get(hdr=self.auth_header, endpoint='/{}/hubs/discover'.format(self.get_cloud_key()))
        if data:
            if identifier:
                for hub in data['MediaContainer']['Hub']:
                    if hub['title'] == identifier:
                        return Hub(hub)
                return None
            return [Hub(hub) for hub in data['MediaContainer']['Hub']]
        return None

    def get_dvr_schedule(self):
        data = self.get(hdr=self.auth_header, endpoint='/media/subscriptions/scheduled')
        if data:
            return DVRSchedule(data.get('MediaContainer'))
        return None

    def get_dvr_items(self):
        data = self.get(hdr=self.auth_header, endpoint='/media/subscriptions')
        if data:
            return [DVRItem(item) for item in data.get('MediaContainer').get('MediaSubscription')]
        return None

    def delete_dvr_item(self, itemID):
        data = self.delete(hdr=self.auth_header, endpoint='/media/subscription/{}'.format(itemID))
        if str(data.status_code).startswith('2'):
            return True
        return False

    def get_homepage_items(self):
        data = self.get(hdr=self.auth_header, endpoint='/hubs')
        if data:
            return [Hub(item) for item in data.get('MediaContainer').get('Hub')]
        return None
