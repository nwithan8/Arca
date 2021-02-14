import socket
import json
import os
from urllib.parse import urlencode

import requests

import helper.utils as utils
from media_server.database import DiscordMediaServerConnectorDatabase


def _save_token_id(file, credentials):
    with open(file, 'w+') as f:
        for line in credentials:
            f.write(f"{line}\n")


class JellyfinItem:
    def __init__(self, data):
        self.id = data['ItemId']
        self.name = data['Name']


class JellyfinPlaylist:
    def __init__(self, data):
        self.id = data['Id']


class JellyfinUser:
    def __init__(self, data):
        self.id = data['Id']
        self.name = data['Name']
        self.password = data.get('Password')


class JellyfinInstance:
    def __init__(self,
                 jellyfin_credentials: dict,
                 jellyfin_token_file_path: str,
                 database: DiscordMediaServerConnectorDatabase):
        self.url = jellyfin_credentials.get('server_url')
        self.api_key = jellyfin_credentials.get('server_api_key')
        self.admin_username = jellyfin_credentials.get('admin_username')
        self.admin_password = jellyfin_credentials.get('admin_password')

        self.default_policy = jellyfin_credentials.get('default_user_policy')
        self.server_name = jellyfin_credentials.get('server_name')
        self.libraries = jellyfin_credentials.get('libraries')

        self._session = requests.Session()
        self.database = database

        self.token_file = jellyfin_token_file_path
        self.admin_id = None
        self.token_header = None
        self.authenticate(force_new_auth=True, token_file=jellyfin_token_file_path)

    def _load_token_id(self, file: str):
        if os.path.exists(file):
            with open(file, 'r') as f:
                lines = f.readlines()
                self.token_header = {'X-Emby-Token': f'{lines[0].rstrip()}'}
                self.admin_id = lines[1].rstrip()
            return True
        return False

    def authenticate(self, force_new_auth: bool = False, token_file: str = None):
        if force_new_auth or not self.token_header:
            x_emby_auth = {
                'X-Emby-Authorization': f'Emby UserId="", '
                                        f'Client="Arca", '
                                        f'Device="{socket.gethostname()}", '
                                        f'DeviceId="{hash(socket.gethostname())}", '
                                        f'Version="1", '
                                        f'Token=""'}
            data = {'Username': self.admin_username,
                    'Password': self.admin_password,
                    'Pw': self.admin_password}
            try:
                res = self._post_request_with_body(hdr=x_emby_auth,
                                                    cmd='/Users/AuthenticateByName',
                                                    data=data).json()
                self.token_header = {'X-Emby-Token': f"{res['AccessToken']}"}
                self.admin_id = res['User']['Id']
                _save_token_id(file=token_file,
                               credentials=[res['AccessToken'], res['User']['Id']])
            except Exception as e:
                raise Exception('Could not log into Jellyfin.\n{}'.format(e))

    def _make_url(self, cmd: str, params: dict = {}, include_api_key: bool = False):
        self.authenticate()
        if not cmd.startswith("/"):
            cmd = f"/{cmd}"
        url = f"{self.url}{cmd}"
        if include_api_key:
            params['api_key'] = self.api_key
        if params or include_api_key:
            url += f"?{urlencode(params)}"
        return url


    def _get_request(self, cmd: str, params: dict = None):
        try:
            url = self._make_url(cmd=cmd, params=params, include_api_key=True)
            res = self._session.get(url=url)
            if res:
                return res.json()
        except:
            pass
        return {}

    def _get_request_with_body(self, hdr: dict, cmd: str, data: dict = None):
        try:
            url = self._make_url(cmd=cmd, include_api_key=False)
            hdr = {'accept': 'application/json', **hdr}
            res = self._session.get(url=url, headers=hdr, data=(json.dumps(data) if data else None))
            if res:
                return res.json()
        except:
            pass
        return {}

    def _post_request(self, cmd: str, params: dict = None, payload: dict = None):
        try:
            url = self._make_url(cmd=cmd, params=params, include_api_key=True)
            res = self._session.post(url=url, json=payload)
            if res:
                return res
        except:
            pass
        return None

    def _post_request_with_body(self, hdr: dict, cmd: str, data: dict = None):
        try:
            url = self._make_url(cmd=cmd, include_api_key=False)
            hdr = {'accept': 'application/json', 'Content-Type': 'application/json', **hdr}
            res = self._session.post(url=url, headers=hdr, data=(json.dumps(data) if data else None))
            if res:
                return res
        except:
            pass
        return None

    def _delete_request(self, cmd: str, params: dict = None):
        try:
            url = self._make_url(cmd=cmd, params=params, include_api_key=True)
            res = self._session.delete(url=url)
            if res:
                return res.json()
        except:
            pass
        return {}

    def make_user(self, username):
        cmd = '/Users/New'
        data = {
            'Name': str(username)
        }
        res = self._post_request(cmd=cmd, params=None, payload=data)
        if res:
            return utils.StatusResponse(success=True, attachment=JellyfinUser(data=res.json()))
        return utils.StatusResponse(success=False, issue=res.content.decode("utf-8"))

    def add_user(self, username):
        return self.make_user(username=username)

    def disable_user(self, user_id, enable=False):
        payload = {
            "IsDisabled": True,
        }
        if enable:
            payload['IsDisabled'] = False
        return self.update_policy(user_id, policy=payload)

    def delete_user(self, user_id):
        cmd = f'/Users/{user_id}'
        return self._delete_request(cmd=cmd, params=None)

    def reset_password(self, user_id):
        cmd = f'/Users/{user_id}/Password'
        data = {
            'Id': str(user_id),
            'ResetPassword': 'true'
        }
        res = self._post_request_with_body(hdr=self.token_header, cmd=cmd, data=data)
        if res:
            return utils.StatusResponse(success=True)
        return utils.StatusResponse(success=False)

    def set_user_password(self, user_id, currentPass, newPass):
        cmd = f'/Users/{user_id}/Password'
        data = {
            'Id': user_id,
            'CurrentPw': currentPass,
            'NewPw': newPass
        }
        res = self._post_request_with_body(hdr=self.token_header, cmd=cmd, data=data)
        if res:
            return utils.StatusResponse(success=True)
        return utils.StatusResponse(success=False)

    def update_policy(self, user_id, policy=None):
        if not policy:
            policy = self.default_policy
        cmd = f'/Users/{user_id}/Policy'
        res = self._post_request_with_body(hdr=self.token_header, cmd=cmd, data=policy)
        if res:
            return utils.StatusResponse(success=True)
        return utils.StatusResponse(success=False)

    def search(self, keyword):
        cmd = f'/Search/Hints?{urlencode({"SearchTerm": keyword})}'
        res = self._get_request_with_body(hdr=self.token_header, cmd=cmd)
        if not res:
            return []
        res = res['SearchHints']
        items = []
        for item in res:
            items.append(JellyfinItem(data=item))
        return items

    def ping(self):
        cmd = "/Users"
        url = self._make_url(cmd=cmd, include_api_key=True)
        if self._session.get(url=url):
            return True
        return False

    def get_all_libraries(self):
        cmd = '/Library/MediaFolders'
        return self._get_request_with_body(hdr=self.token_header, cmd=cmd)

    def get_user_libraries(self, user_id=None):
        if not user_id:
            user_id = self.admin_id
        cmd = '/Users/{}/Items'.format(str(user_id))
        return self._get_request_with_body(hdr=self.token_header, cmd=cmd)

    def get_users(self):
        # cmd = '/user_usage_stats/user_list'
        cmd = '/Users'
        res = self._get_request(cmd=cmd, params=None)
        users = []
        for user in res:
            users.append(JellyfinUser(data=user))
        return users

    def get_users_short(self):
        cmd = '/user_usage_stats/user_list'
        return self._get_request(cmd=cmd, params=None)

    def get_users_details(self):
        cmd = '/Users'
        return self._get_request(cmd=cmd, params=None)

    def get_user_details(self, user_id):
        for user in self.get_user_details(user_id=user_id):
            if user['Id'] == user_id:
                return user
        return None

    def get_user_config(self, user_id):
        try:
            details = self.get_user_details(user_id=user_id)
            return details.get('Configuration')
        except Exception as e:
            print(f"{e}")
        return None

    def get_user_policy(self, user_id):
        try:
            details = self.get_user_details(user_id=user_id)
            return details.get('Policy')
        except Exception as e:
            print(f"{e}")
        return None

    def get_user_details_simple(self, user_id):
        try:
            details = self.get_user_details(user_id=user_id)
            simplified_details = {
                'Name': details.get('Name'),
                'ServerId': details.get('ServerId'),
                'Id': details.get('Id'),
                'HasPassword': details.get('HasPassword')
            }
            policy = details.get('Policy')
            if policy:
                policy_details = {
                    'Admin': policy.get('IsAdministrator'),
                    'Hidden': policy.get('IsHidden'),
                    'Disabled': policy.get('IsDisabled'),
                    'RemoteControlOfOthers': policy.get('EnableRemoteControlOfOtherUsers'),
                    'SharedDeviceControl': policy.get('EnableShareDeviceControl'),
                    'RemoteAccess': policy.get('EnableRemoteAccess'),
                    'LiveTVManagement': policy.get('EnableLiveTvManagement'),
                    'LiveTVAccess': policy.get('EnableLiveTvAccess'),
                    'MediaPlayback': policy.get('EnableMediaPlayback'),
                    'AudioTranscoding': policy.get('EnableAudioPlaybackTranscoding'),
                    'VideoTranscoding': policy.get('EnableVideoPlaybackTranscoding'),
                    'PlaybackRemuxing': policy.get('EnablePlaybackRemuxing'),
                    'ForceRemoteTranscoding': policy.get('ForceRemoteSourceTranscoding'),
                    'DeleteContent': policy.get('EnableContentDeletion'),
                    'DeleteContentFromFolders': policy.get('EnableContentDeletionFromFolders'),
                    'DownloadContent': policy.get('EnableContentDownloading'),
                    'SyncTranscoding': policy.get('EnableSyncTranscoding'),
                    'MediaConversion': policy.get('EnableMediaConversion'),
                    'EnabledDevices': (
                        True if policy.get('EnableAllDevices') == True else policy.get('EnabledDevices')),
                    'EnabledChannels': (
                        True if policy.get('EnableAllChannels') == True else policy.get('EnabledChannels')),
                    'EnabledFolders': (
                        True if policy.get('EnableAllFolders') == True else policy.get('EnabledFolders')),
                    'RemoteBitrateLimit': policy.get('RemoteClientBitrateLimit'),
                    'PublicSharing': policy.get('EnablePublicSharing'),
                    'InvalidLoginAttempts': policy.get('InvalidLoginAttempts'),
                    'InvalidLoginLockout': (False if policy.get('LoginAttemptsBeforeLockout') == -1 else policy.get(
                        'LoginAttemptsBeforeLockout'))
                }
                user_folders = self.get_user_libraries(user_id=user_id)
                folder_names = []
                if user_folders and user_folders.get('Items'):
                    folder_names = [folder['Name'] for folder in user_folders.get('Items')]
                policy_details['EnabledFolderNames'] = folder_names
                simplified_details.update(policy_details)
            return simplified_details
        except Exception as e:
            print(f"Error in getUserDetailsSimplified: {e}")
        return None

    def update_rating(self, itemId, upvote, user_id):
        cmd = f'/Users/{user_id}/Items/{itemId}/Rating?Likes={upvote}'
        res = self._post_request_with_body(hdr=self.token_header, cmd=cmd)
        if res:
            return True
        return False

    def get_playlists(self, name):
        cmd = f'/Playlists'
        res = self._get_request(cmd=cmd, params=None)
        playlists = []
        for playlist in res:
            playlists.append(JellyfinPlaylist(data=playlist))
        return playlists

    def make_playlists(self, name, user_id):
        cmd = f'/Playlists'
        params = {"Name": name,
                  "UserId": user_id}
        res = self._post_request(cmd=cmd, params=params)
        if res:
            return JellyfinPlaylist(data=res.json())
        return None

    def add_to_playlist(self, playlistId, itemIds, user_id):
        item_list = ','.join(itemIds)
        cmd = f'/Playlists/{playlistId}/Items'
        params = {"Ids": item_list,
                  "UserId": user_id}
        res = self._post_request(cmd=cmd, params=params)
        if res:
            return True
        return False

    def stats_custom_query(self, query):
        cmd = '/user_usage_stats/submit_custom_query'
        return self._post_request(cmd=cmd, params=None, payload=query)

    def get_status(self):
        return requests.get(f'{self.url}/swagger', timeout=10).status_code

    def get_server_info(self):
        return self._get_request(cmd='/System/Info')

    def get_all_sessions(self, params=None):
        return self._get_request_with_body(hdr=self.token_header, cmd='/Sessions', data=params)

    def get_live_sessions(self):
        live_sessions = []
        sessions = self.get_all_sessions(params={'ActiveWithinSeconds': 20})
        for session in sessions:
            if session.get('NowPlayingItem'):
                live_sessions.append(NowPlayingItem(data=session))
        return live_sessions

    def send_play_state_command(self, session_id, command):
        cmd = f'/Sessions/{session_id}/Playing/{command}'
        return self._post_request_with_body(hdr=self.token_header, cmd=cmd)

    def send_message_to_client(self, session_id, message):
        cmd = f'/Sessions/{session_id}/Message'
        return self._post_request_with_body(hdr=self.token_header, cmd=cmd, data={'Text': str(message)})

    def stop_stream(self, stream_id, message_to_viewer=None):
        if message_to_viewer:
            self.send_message_to_client(session_id=stream_id, message=message_to_viewer)
        return self.send_play_state_command(session_id=stream_id, command='Stop')

    def get_username_from_id(self, user_id):
        user_list = self.get_users_short()
        for user in user_list:
            if user.get('id') == user_id:
                return user.get('name')
        return None

    def get_user_id_from_username(self, username):
        user_list = self.get_users_short()
        for user in user_list:
            if user.get('name') == username:
                return user.get('id')
        return None

    def get_defined_libraries(self):
        nicknames = [name for name in self.libraries.keys()]
        names = []
        for _, v in self.libraries.items():
            if v not in names:
                names.append(v)
        return {'Nicknames': nicknames, 'Full Names': names}

    def get_library_name_from_id(self, library_id):
        libraries = self.get_all_libraries()
        for lib in libraries['Items']:
            if lib['Id'] == library_id:
                return lib['Name']
        return None

    def get_library_id_from_name(self, library_name):
        libraries = self.get_all_libraries()
        for lib in libraries['Items']:
            if lib['Name'] == library_name:
                return lib['Id']
        return None

    def get_suggestion_by_user_id(self, user_id, media="Movie,Episode", limit=1):
        """
        ONLY WORKS FOR CURRENTLY-AUTHENTICATED USER
        """
        return self._get_request_with_body(hdr=self.token_header,
                                           cmd=f"/Users/{user_id}/Suggestions?type={media}&limit={limit}")


class NowPlayingItem:
    def __init__(self, data):
        self.sessionId = data['Id']
        self.userId = data['UserId']
        self.username = data['UserName']
        self.mediaType = data['NowPlayingItem']['MediaType']
        self.videoType = data['NowPlayingItem']['Type']
        self.title = data['NowPlayingItem']['Name']
        self.summary = data['NowPlayingItem']['Overview']
        self.path = data['NowPlayingItem']['Path']
        self.mediaId = data['NowPlayingItem']['Id']
        self.seasonTitle = None
        self.seasonId = None
        self.seriesTitle = None
        self.seriesId = None
        if self.videoType == 'Episode':
            self.seasonTitle = data['NowPlayingItem']['SeasonName']
            self.seasonId = data['NowPlayingItem']['SeasonId']
            self.seriesTitle = data['NowPlayingItem']['SeriesName']
            self.seriesId = data['NowPlayingItem']['SeriesId']
        self.container = data['NowPlayingItem']['Container']
        self.dateCreated = data['NowPlayingItem']['Container']
        self.width = data['NowPlayingItem']['Width']
        self.height = data['NowPlayingItem']['Height']
        self.method = data['PlayState']['PlayMethod']
        self.state = ('Paused' if data['PlayState']['IsPaused'] else 'Playing')
        self.client = data['Client']
        self.deviceId = data['DeviceId']
        self.deviceName = data['DeviceName']
