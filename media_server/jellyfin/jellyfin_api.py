import requests
import socket
import json
import os
from urllib.parse import urlencode
from media_server.jellyfin import settings as settings


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


class JellyfinInstance:
    def __init__(self, url, api_key, admin_username, admin_password, default_policy, server_name,
                 token_file='.jellyfin_token'):
        self.url = url
        self.api_key = api_key
        self.admin_username = admin_username
        self.admin_password = admin_password
        self.admin_id = None

        self.default_policy = default_policy
        self.server_name = server_name

        self.token_header = None
        self.authenticate(token_file=token_file)

    def _load_token_id(self, file):
        if os.path.exists(file):
            with open(file, 'r') as f:
                lines = f.readlines()
                self.token_header = {'X-Emby-Token': f'{lines[0].rstrip()}'}
                self.admin_id = lines[1].rstrip()
            return True
        return False

    def authenticate(self, force_new_auth: bool = False, token_file=None):
        if force_new_auth or not self._load_token_id(token_file):
            xEmbyAuth = {
                'X-Emby-Authorization': 'Emby UserId="{UserId}", Client="{Client}", Device="{Device}", '
                                        'DeviceId="{DeviceId}", Version="{Version}", Token="{Token}'.format(
                    UserId="",  # not required, if it was we would have to first request the UserId from the username
                    Client='Arca',
                    Device=socket.gethostname(),
                    DeviceId=hash(socket.gethostname()),
                    Version=1,
                    Token=""  # not required
                )}
            data = {'Username': self.admin_username, 'Password': self.admin_password,
                    'Pw': self.admin_password}
            try:
                res = self._post_request_with_token(hdr=xEmbyAuth, cmd='/Users/AuthenticateByName', data=data).json()
                self.token_header = {'X-Emby-Token': '{}'.format(res['AccessToken'])}
                self.admin_id = res['User']['Id']
                _save_token_id(file=token_file, credentials=[res['AccessToken'], res['User']['Id']])
            except Exception as e:
                raise Exception('Could not log into Jellyfin.\n{}'.format(e))

    def _get_request(self, cmd, params=None):
        try:
            res = requests.get(f'{self.url}{cmd}?api_key={self.api_key}{("&" + params if params else "")}')
            if res:
                return res.json()
        except:
            pass
        return {}

    def _get_request_with_token(self, hdr, cmd, data=None):
        try:
            hdr = {'accept': 'application/json', **hdr}
            res = requests.get(f'{self.url}{cmd}', headers=hdr, data=(json.dumps(data) if data else None))
            if res:
                return res.json()
        except:
            pass
        return {}

    def _post_request(self, cmd, params=None, payload=None):
        try:
            res = requests.post(
                f'{self.url}{cmd}?api_key={self.api_key}{("&" + params if params is not None else "")}', json=payload)
            if res:
                return res
        except:
            pass
        return None

    def _post_request_with_token(self, hdr, cmd, data=None):
        try:
            hdr = {'accept': 'application/json', 'Content-Type': 'application/json', **hdr}
            res = requests.post(f'{self.url}{cmd}', headers=hdr, data=(json.dumps(data) if data else None))
            if res:
                return res
        except:
            pass
        return None

    def _delete_request(self, cmd, params=None):
        try:
            res = requests.delete(
                f'{self.url}{cmd}?api_key={self.api_key}{("&" + params if params is not None else "")}')
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
            return JellyfinUser(data=res.json()), None
        return None, res.content.decode("utf-8")

    def disable_user(self, userId, enable=False):
        payload = {
            "IsDisabled": True,
        }
        if enable:
            payload['IsDisabled'] = False
        return self.update_policy(userId, policy=payload)

    def delete_user(self, userId):
        cmd = f'/Users/{userId}'
        return self._delete_request(cmd=cmd, params=None)

    def reset_password(self, userId):
        cmd = f'/Users/{userId}/Password'
        data = {
            'Id': str(userId),
            'ResetPassword': 'true'
        }
        res = self._post_request_with_token(hdr=self.token_header, cmd=cmd, data=data)
        if res:
            return True
        return False

    def set_user_password(self, userId, currentPass, newPass):
        cmd = f'/Users/{userId}/Password'
        data = {
            'Id': userId,
            'CurrentPw': currentPass,
            'NewPw': newPass
        }
        res = self._post_request_with_token(hdr=self.token_header, cmd=cmd, data=data)
        if res:
            return True
        return False

    def update_policy(self, userId, policy=None):
        if not policy:
            policy = self.default_policy
        cmd = f'/Users/{userId}/Policy'
        res = self._post_request_with_token(hdr=self.token_header, cmd=cmd, data=policy)
        if res:
            return True
        return False

    def search(self, keyword):
        cmd = f'/Search/Hints?{urlencode({"SearchTerm": keyword})}'
        res = self._get_request_with_token(hdr=self.token_header, cmd=cmd)
        if not res:
            return []
        res = res['SearchHints']
        items = []
        for item in res:
            items.append(JellyfinItem(data=item))
        return items

    def get_all_libraries(self):
        cmd = '/Library/MediaFolders'
        return self._get_request_with_token(hdr=self.token_header, cmd=cmd)

    def get_user_libraries(self, user_id=None):
        if not user_id:
            user_id = self.admin_id
        cmd = '/Users/{}/Items'.format(str(user_id))
        return self._get_request_with_token(hdr=self.token_header, cmd=cmd)

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
                policyDetails = {
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
                policyDetails['EnabledFolderNames'] = folder_names
                simplified_details.update(policyDetails)
            return simplified_details
        except Exception as e:
            print(f"Error in getUserDetailsSimplified: {e}")
        return None

    def update_rating(self, itemId, upvote, userId):
        cmd = f'/Users/{userId}/Items/{itemId}/Rating?Likes={upvote}'
        res = self._post_request_with_token(hdr=self.token_header, cmd=cmd)
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

    def make_playlists(self, name, userId):
        cmd = f'/Playlists'
        params = f'{urlencode({"Name": name})}&UserId={userId}'
        res = self._post_request(cmd=cmd, params=params)
        if res:
            return JellyfinPlaylist(data=res.json())
        return None

    def add_to_playlist(self, playlistId, itemIds, userId):
        item_list = ','.join(itemIds)
        cmd = f'/Playlists/{playlistId}/Items'
        params = f'Ids={item_list}&UserId={userId}'
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
        return self._get_request_with_token(hdr=self.token_header, cmd='/Sessions', data=params)

    def get_live_sessions(self):
        live_sessions = []
        sessions = self.get_all_sessions(params={'ActiveWithinSeconds': 20})
        for session in sessions:
            if session.get('NowPlayingItem'):
                live_sessions.append(NowPlayingItem(data=session))
        return live_sessions

    def send_play_state_command(self, session_id, command):
        cmd = f'/Sessions/{session_id}/Playing/{command}'
        return self._post_request_with_token(hdr=self.token_header, cmd=cmd)

    def send_message_to_client(self, session_id, message):
        cmd = f'/Sessions/{session_id}/Message'
        return self._post_request_with_token(hdr=self.token_header, cmd=cmd, data={'Text': str(message)})

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
        nicknames = [name for name in settings.JELLYFIN_LIBRARIES.keys()]
        names = []
        for _, v in settings.JELLYFIN_LIBRARIES.items():
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
        return self._get_request_with_token(hdr=self.token_header,
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
