from typing import Union, List, Tuple
import re
import json
import xml.etree.ElementTree as ET
from collections import defaultdict

import requests
from plexapi.myplex import MyPlexUser
from plexapi.server import PlexServer
from plexapi import exceptions as plex_exceptions

import helper.utils as utils
from helper.encryption import Encryption
from media_server.connectors.ombi_connector import OmbiConnector
from media_server.connectors.tautulli_connector import TautulliConnector
from media_server.media_server_database import DiscordMediaServerConnectorDatabase

all_movie_ratings = ['12', 'Approved', 'Passed', 'G', 'GP', 'PG', 'PG-13', 'M', 'R', 'NC-17', 'Unrated', 'Not Rated',
                     'NR', 'None']
all_tv_ratings = ['TV-Y', 'TV-Y7', 'TV-G', 'TV-PG', 'TV-14', 'TV-MA', 'NR']


class PlexInstance:
    def __init__(self,
                 url: str,
                 token: str,
                 api,
                 server_name: str = None,
                 server_alt_name: str = None,
                 server_number: int = 0,
                 credentials_folder: str = None,
                 tautulli_info=None,
                 ombi_info=None,
                 libraries=None):
        # Server info
        self.url = url
        self.token = token
        if not url or not token:
            raise Exception("Must include Plex Media Server url and token")
        self._api = api
        self.server = PlexServer(self.url, self.token)
        self.name = server_name if server_name else self.server.friendlyName
        self.alt_name = server_alt_name if server_alt_name else self.server.friendlyName
        self.number = server_number
        self.id = self.server.machineIdentifier

        # Auth
        self.auth_header = {'X-Plex-Token': token}
        self.cloud_key = None

        # Crypt
        self.crypt = None
        if credentials_folder:
            self.crypt = Encryption(key_file=f'{credentials_folder}/key.txt', key_folder=credentials_folder)

        # Libraries
        self.shows = defaultdict(list)
        self.movies = defaultdict(list)
        self.libraries = libraries

        # Ombi
        self.use_ombi = False
        self.ombi = None
        if ombi_info:
            self.set_ombi_connection(ombi_info)

        # Tautulli
        self.use_tautulli = False
        self.tautulli = None
        if tautulli_info:
            self.set_tautulli_connection(tautulli_info)

    def set_tautulli_connection(self, tautulli_info):
        self.use_tautulli = tautulli_info.get('enable', False)
        if self.use_tautulli:
            self.tautulli = TautulliConnector(url=tautulli_info.get('url'), api_key=tautulli_info.get('api_key'))

    def set_ombi_connection(self, ombi_info):
        self.use_ombi = ombi_info.get('enable', False)
        if self.use_ombi:
            self.ombi = OmbiConnector(url=ombi_info.get('url'), api_key=ombi_info.get('api_key'))

    def get_user_creds(self, user_id) -> dict:
        if self.crypt:
            creds_dict = {'username': None, 'password': None}
            if self.crypt.exists(f"{user_id}.json"):
                creds = self.crypt.decrypt_file(f'{self.crypt.key_folder}/{user_id}.json').splitlines()
                creds_dict = {'username': creds[0], 'password': creds[1]}
            return creds_dict
        return {}

    def ping(self) -> bool:
        response = requests.get(f"{self.url}/identity", timeout=10)
        if response:
            return True
        return False

    def save_user_creds(self, user_id, username, password) -> bool:
        if self.crypt:
            text = '{}\n{}'.format(username, password)
            return self.crypt.encrypt_file(text=text, filename=f'{self.crypt.key_folder}/{user_id}.json')
        return False

    def get_media_item(self, title: str, rating_key=None, library_id=None):
        library = self.server.library
        if library_id:
            library = library.sectionByID(str(library_id))
        results = library.search(title=title)
        if results:
            if rating_key:  # find exact match
                for item in results:
                    if item.ratingKey == rating_key:
                        return item
            return results[0]  # assume first result is correct
        return None

    def get_watch_now_link(self, rating_key: str) -> str:
        return f"https://app.plex.tv/desktop#!/server/{self.id}//details?key=%2Flibrary%2Fmetadata%2F{rating_key}"

    def get_media_info(self, rating_key) -> Tuple[str, str]:
        r = requests.get(f'{self.url}/library/metadata/{rating_key}?X-Plex-Token={self.token}').content
        tree = ET.fromstring(r)
        return tree.get('librarySectionID'), tree[0].get('title')

    def get_rating_key(self, url=None) -> str:
        if not url:
            url = self.url
        return str(re.search('metadata%2F(\d*)', url).group(1))

    def find_url(self, text) -> str:
        pattern = '{}\S*'.format(self.url.replace('.', '\.'))
        return str(re.search(pattern, text).group(0))

    def get_playlist(self, playlist_name):
        for playlist in self.server.playlists():
            if playlist.title == playlist_name:
                return playlist
        return None

    def add_to_playlist(self, playlist_title, rating_key, item_to_add) -> str:
        playlist = self.get_playlist(playlist_name=playlist_title)
        if playlist:
            for item in playlist.items():
                if str(item.ratingKey) == str(rating_key):
                    return "That item is already on your {}list".format(
                        'play' if item_to_add.type in ['artist', 'track', 'album'] else 'watch')
            playlist.addItems([item_to_add])
            return "Item added to your {}list".format(
                'play' if item_to_add.type in ['artist', 'track', 'album'] else 'watch')
        else:
            self.server.createPlaylist(title=playlist_title, items=[item_to_add])
            return "New {}list created and item added.".format(
                'play' if item_to_add.type in ['artist', 'track', 'album'] else 'watch')

    def url_in_message(self, message) -> Union[str, None]:
        server_id = self.server.machineIdentifier
        if server_id in message.content and 'metadata%2F' in message.content:
            return self.find_url(text=message.content)
        if message.embeds:
            for embed in message.embeds:
                if server_id in embed.title and 'metadata%2F' in embed.title:
                    return self.find_url(text=embed.title)
                elif server_id in embed.description and 'metadata%2F' in embed.description:
                    return self.find_url(embed.description)
                elif server_id in embed.description and 'metadata%2F' in embed.url:
                    return self.find_url(embed.url)
            return None
        return None

    @property
    def sub_count(self) -> int:
        count = 0
        for user in self.server.myPlexAccount().users():
            for server in user.servers:
                if server.name in [self.name, self.alt_name]:
                    count += 1
                    break
        return count

    @property
    def users(self) -> List[MyPlexUser]:
        try:
            return self.server.myPlexAccount().users()
        except Exception as e:
            print(f"Error in getServerUsers: {e}")
        return []

    def get_user(self, username) -> Union[MyPlexUser, None]:
        try:
            return self.server.myPlexAccount().user(username=username)
        except Exception as e:
            print(f"Error in getServerUser: {e}")
        return None

    @property
    def plex_friends(self) -> List[MyPlexUser]:
        """
        # Returns all Plex Friends (access in + access out)
        """
        friends = []
        for user in self.users:
            if user.friend:
                friends.append(user)
        return friends

    def user_has_access(self, plex_username: str) -> bool:
        for user in self.users:
            if user.username == plex_username:
                return True
        return False

    def add_user(self, plex_username: str) -> utils.StatusResponse:
        try:
            self.server.myPlexAccount().inviteFriend(user=plex_username, server=self.server,
                                                     sections=None,
                                                     allowSync=False,
                                                     allowCameraUpload=False,
                                                     allowChannels=False,
                                                     filterMovies=None,
                                                     filterTelevision=None,
                                                     filterMusic=None)
            return utils.StatusResponse(success=True)
        except plex_exceptions.NotFound:
            return utils.StatusResponse(success=False, issue="Invalid Plex username")
        except Exception as e:
            return utils.StatusResponse(success=False, issue=e.__str__())

    def remove_user(self, plex_username: str) -> utils.StatusResponse:
        try:
            self.server.myPlexAccount().removeFriend(user=plex_username)
            return utils.StatusResponse(success=True)
        except plex_exceptions.NotFound:
            return utils.StatusResponse(success=False, issue="Invalid Plex username")
        except Exception as e:
            return utils.StatusResponse(success=False, issue=e.__str__())

    def refresh_tautulli_users(self) -> bool:
        if self.use_tautulli:
            return self.tautulli.refresh_users()
        return False

    def delete_user_from_tautulli(self, plex_username) -> bool:
        if self.use_tautulli:
            return self.tautulli.delete_user(plex_username=plex_username)
        return False

    def refresh_ombi_users(self) -> bool:
        if self.use_ombi:
            return self.ombi.refresh_users()
        return False

    def delete_user_from_ombi(self, username: str) -> bool:
        if self.use_ombi:
            return self.ombi.delete_user(plex_username=username)
        return False

    def get_live_tv_dvrs(self):
        data = self._get(hdr=self.auth_header, endpoint='/livetv/dvrs')
        if data:
            if data.get('MediaContainer').get('Dvr'):
                return [DVR(item) for item in data.get('MediaContainer').get('Dvr')]
        return None

    def get_cloud_key(self):
        if not self.cloud_key:
            data = self._get(hdr=self.auth_header, endpoint='/tv.plex.providers.epg.cloud')
            if data:
                self.cloud_key = data.get('MediaContainer').get('Directory')[1].get('title')
            else:
                return None
        return self.cloud_key

    def get_live_tv_sessions(self):
        data = self._get(hdr=self.auth_header, endpoint='/livetv/sessions')
        if data:
            if data.get('MediaContainer').get('Metadata'):
                return [TVSession(item) for item in data.get('MediaContainer').get('Metadata')]
        return None

    def get_hubs(self, identifier=None):
        data = self._get(hdr=self.auth_header, endpoint=f'/{self.get_cloud_key()}/hubs/discover')
        if data:
            if identifier:
                for hub in data['MediaContainer']['Hub']:
                    if hub['title'] == identifier:
                        return Hub(hub)
                return None
            return [Hub(hub) for hub in data['MediaContainer']['Hub']]
        return None

    def get_dvr_schedule(self):
        data = self._get(hdr=self.auth_header, endpoint='/media/subscriptions/scheduled')
        if data:
            return DVRSchedule(data.get('MediaContainer'))
        return None

    def get_dvr_items(self):
        data = self._get(hdr=self.auth_header, endpoint='/media/subscriptions')
        if data:
            return [DVRItem(item) for item in data.get('MediaContainer').get('MediaSubscription')]
        return None

    def delete_dvr_item(self, itemID):
        data = self._delete(hdr=self.auth_header, endpoint='/media/subscription/{}'.format(itemID))
        if str(data.status_code).startswith('2'):
            return True
        return False

    def get_homepage_items(self):
        data = self._get(hdr=self.auth_header, endpoint='/hubs')
        if data:
            return [Hub(item) for item in data.get('MediaContainer').get('Hub')]
        return None

    def _get(self, hdr, endpoint, data=None):
        """ Returns JSON """
        hdr = {'accept': 'application/json', **hdr}
        res = requests.get(f'{self.url}{endpoint}', headers=hdr, data=json.dumps(data)).json()
        return res

    def _post(self, hdr, endpoint, data=None) -> requests.Response:
        """ Returns response """
        hdr = {'accept': 'application/json', **hdr}
        res = requests.post(f'{self.url}{endpoint}', headers=hdr, data=json.dumps(data))
        return res

    def _delete(self, hdr, endpoint, data=None) -> requests.Response:
        """ Returns response """
        hdr = {'accept': 'application/json', **hdr}
        res = requests.delete(f'{self.url}{endpoint}', headers=hdr, data=json.dumps(data))
        return res

    def get_defined_libraries(self):
        names = [name for name in self.libraries.keys()]
        ids = []
        for _, vs in self.libraries.items():
            for v in vs:
                if v not in ids:
                    ids.append(str(v))
        return {'names': names, 'IDs': ids}

    def get_plex_share(self, share_name_or_number):
        if not self.libraries:
            return False
        if utils.is_positive_int(share_name_or_number):
            return [int(share_name_or_number)]
        else:
            for name, numbers in self.libraries.items():
                if name == share_name_or_number:
                    return numbers
            return False

    def _get_server_from_user_share(self, plex_user):
        try:
            return plex_user.server(self.name)
        except:
            return plex_user.server(self.alt_name)

    def get_user_restrictions(self, plex_username):
        user = self.get_user(username=plex_username)
        if user:
            if user.friend:
                try:
                    sections = self._get_server_from_user_share(plex_user=user).sections()
                except:
                    raise Exception("Could not load Plex user sections.")
                return {'allowSync': user.allowSync,
                        'filterMovies': user.filterMovies,
                        'filterShows': user.filterTelevision,
                        'sections': ([section.title for section in sections] if sections else [])
                        }
            else:
                raise Exception(f"Plex user {plex_username} is not a Plex Friend.")
        else:
            raise Exception(f"Could not locate Plex user: {plex_username}")

    def update_user_restrictions(self, plex_username, sections_to_share=[], rating_limit={},
                                 allow_sync: bool = None) -> bool:
        """
        :param plex_username:
        :param sections_to_share:
        :param rating_limit: ex. {'Movie': 'PG-13', 'TV': 'TV-14'}
        :param allow_sync:
        :return:
        """
        try:
            sections = []
            for section in sections_to_share:
                section_numbers = self.get_plex_share(share_name_or_number=section)
                if section_numbers:
                    for number in section_numbers:
                        sections.append(str(number))
            allowed_movie_ratings = []
            allowed_tv_ratings = []
            if rating_limit:
                # add max rating and all below it to allowed ratings
                # if non_existent rating is used as limit, all ratings will be added
                if rating_limit.get('Movie') and rating_limit.get('Movie') in all_movie_ratings:
                    for rating in all_movie_ratings:
                        allowed_movie_ratings.append(rating)
                        if rating == rating_limit.get('Movie'):
                            break
                if rating_limit.get('TV') and rating_limit.get('TV') in all_tv_ratings:
                    for rating in all_tv_ratings:
                        allowed_tv_ratings.append(rating)
                        if rating == rating_limit.get('TV'):
                            break
            self.server.myPlexAccount().updateFriend(user=plex_username,
                                                     server=self.server,
                                                     sections=(sections if sections else None),
                                                     removeSections=False,
                                                     allowSync=allow_sync,
                                                     allowCameraUpload=None,
                                                     allowChannels=None,
                                                     filterMovies=(
                                                         {
                                                             'contentRating': allowed_movie_ratings} if allowed_movie_ratings else None
                                                     ),
                                                     filterTelevision=(
                                                         {
                                                             'contentRating': allowed_tv_ratings} if allowed_tv_ratings else None
                                                     ),
                                                     filterMusic=None)
            return True
        except:
            print(f"Could not update restrictions for Plex user: {plex_username}")
            return False


class PlexConnections:
    def __init__(self,
                 plex_credentials: dict,
                 database: DiscordMediaServerConnectorDatabase):
        """
        :param plex_credentials: {1: {'url', 'token', 'name', 'altname', 'credsfolder', 'tautulli': {'url', 'api_key'}, 'ombi': {'url', 'api_key'}}, 'libraries': {'movies': [1], 'shows': [2, 3]}}
        """
        self._credentials = plex_credentials
        self.database = database

    def close_database(self):
        self.database.close()

    @property
    def plex_connectors(self) -> dict:
        connectors = {}
        for server_number, info in self._credentials.items():
            connectors[int(server_number)] = PlexInstance(url=info.get('server_url'),
                                                          token=info.get('server_token'),
                                                          api=self,
                                                          server_name=info.get('server_name'),
                                                          server_alt_name=info.get('alternate_server_name'),
                                                          server_number=server_number,
                                                          credentials_folder=info.get('user_credentials_folder'),
                                                          tautulli_info=info.get('tautulli'),
                                                          ombi_info=info.get('ombi'),
                                                          libraries=info.get('libraries')
                                                          )
        return connectors

    def get_plex_instance(self, server_number: int = None) -> Union[PlexInstance, None]:
        if server_number:
            return self.plex_connectors.get(server_number, None)
        return self.all_plex_instances[0]

    @property
    def all_plex_instances(self) -> List[PlexInstance]:
        return [connector for _, connector in self.plex_connectors.items()]

    @property
    def smallest_server(self) -> PlexInstance:
        smallest_count = 100
        smallest_server = self.plex_connectors[0]
        for server_number, plex_connection in self.plex_connectors.items():
            user_count = plex_connection.sub_count
            if user_count < smallest_count:
                smallest_count = user_count
                smallest_server = plex_connection
        return smallest_server

    def add_user_to_smallest_server(self, plex_username: str) -> bool:
        smallest_server = self.smallest_server
        return smallest_server.add_user(plex_username=plex_username)

    def add_user_to_specific_server(self, plex_username: str, server_number: int = 0, plex_connection=None) -> bool:
        if not plex_connection:
            plex_connection = self.plex_connectors[server_number]
        if plex_connection.add_user_to_plex(plex_username=plex_username):
            return True
        return False

    def add_user_to_all_servers(self, plex_username: str) -> bool:
        for server_number, plex_connection in self.plex_connectors.items():
            plex_connection.add_user(plex_username=plex_username)
        return True

    def remove_user_from_specific_server(self, plex_username: str, server_number: int = 0,
                                         plex_connection=None) -> bool:
        if not plex_connection:
            plex_connection = self.plex_connectors[server_number]
        if plex_connection.remove_user_from_plex(plex_username=plex_username):
            return True
        return False

    def remove_user_from_all_servers(self, plex_username: str) -> bool:
        for server_number, plex_connection in self.plex_connectors.items():
            plex_connection.remove_user(plex_username=plex_username)
        return True

    def refresh_specific_tautulli(self, server_number: int, plex_connection=None) -> bool:
        if not plex_connection:
            plex_connection = self.plex_connectors[server_number]
        if plex_connection.use_tautulli:
            plex_connection.refresh_tautulli_users()
        return True

    def refresh_all_tautullis(self) -> bool:
        for server_number, plex_connection in self.plex_connectors.items():
            if plex_connection.use_tautulli:
                plex_connection.refresh_tautulli_users()
        return True

    def remove_user_from_specific_tautulli(self, plex_username: str, server_number: int = 0,
                                           plex_connection=None) -> bool:
        if not plex_connection:
            plex_connection = self.plex_connectors[server_number]
        if plex_connection.use_tautulli:
            return plex_connection.delete_user_from_tautulli(plex_username=plex_username)
        return False

    def remove_user_from_all_tautullis(self, plex_username: str) -> bool:
        for server_number, plex_connection in self.plex_connectors.items():
            if plex_connection.use_tautulli:
                plex_connection.delete_user_from_tautulli(plex_username=plex_username)
        return True

    def refresh_specific_ombi(self, server_number: int, plex_connection=None) -> bool:
        if not plex_connection:
            plex_connection = self.plex_connectors[server_number]
        if plex_connection.use_ombi:
            return plex_connection.refresh_ombi_users()
        return False

    def refresh_all_ombis(self) -> bool:
        for server_number, plex_connection in self.plex_connectors.items():
            if plex_connection.use_ombi:
                plex_connection.refresh_ombi_users()
        return True

    def remove_user_from_specific_ombi(self, plex_username: str, server_number: int = 0, plex_connection=None) -> bool:
        if not plex_connection:
            plex_connection = self.plex_connectors[server_number]
        if plex_connection.use_ombi:
            return plex_connection.delete_user_from_ombi(username=plex_username)
        return False

    def remove_user_from_all_ombis(self, plex_username: str) -> bool:
        for server_number, plex_connection in self.plex_connectors.items():
            if plex_connection.use_ombi:
                plex_connection.delete_user_from_ombi(username=plex_username)
        return True


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
