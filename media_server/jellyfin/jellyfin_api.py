import requests
import socket
import json
from urllib.parse import urlencode
from media_server.jellyfin import settings as settings

token_header = None
admin_id = None


def authenticate():
    global token_header
    global admin_id
    xEmbyAuth = {
        'X-Emby-Authorization': 'Emby UserId="{UserId}", Client="{Client}", Device="{Device}",'
                                'DeviceId="{DeviceId}", Version="{Version}", Token="""'.format(
            UserId="",  # not required, if it was we would have to first request the UserId from the username
            Client='account-automation',
            Device=socket.gethostname(),
            DeviceId=hash(socket.gethostname()),
            Version=1,
            Token=""  # not required
        )
    }
    data = {'Username': settings.JELLYFIN_ADMIN_USERNAME, 'Password': settings.JELLYFIN_ADMIN_PASSWORD,
            'Pw': settings.JELLYFIN_ADMIN_PASSWORD}
    try:
        res = postWithToken(hdr=xEmbyAuth, url='/Users/AuthenticateByName', data=data).json()
        token_header = {'X-Emby-Token': '{}'.format(res['AccessToken'])}
        admin_id = res['User']['Id']
    except Exception as e:
        print('Could not log into Jellyfin.\n{}'.format(e))


def get(cmd, params=None):
    return json.loads(requests.get(
        '{}{}?api_key={}{}'.format(settings.JELLYFIN_URL, cmd, settings.JELLYFIN_API_KEY,
                                   ("&" + params if params else ""))).text)


def getWithToken(hdr, url, data=None):
    hdr = {'accept': 'application/json', **hdr}
    return requests.get('{}{}'.format(settings.JELLYFIN_URL, url), headers=hdr, params=data).json()


def post(cmd, params, payload):
    return requests.post(
        '{}{}?api_key={}{}'.format(settings.JELLYFIN_URL, cmd, settings.JELLYFIN_API_KEY,
                                   ("&" + params if params is not None else "")),
        json=payload)


def postWithToken(hdr, url, data=None):
    hdr = {'accept': 'application/json', 'Content-Type': 'application/json', **hdr}
    return requests.post('{}{}'.format(settings.JELLYFIN_URL, url), headers=hdr, data=json.dumps(data))


def delete(cmd, params):
    return requests.delete(
        '{}{}?api_key={}{}'.format(settings.JELLYFIN_URL, cmd, settings.JELLYFIN_API_KEY,
                                   ("&" + params if params is not None else "")))


def deleteWithToken(hdr, url, data=None):
    hdr = {'accept': 'application/json', **hdr}
    return requests.delete('{}{}'.format(settings.JELLYFIN_URL, url), headers=hdr, data=json.dumps(data))


def makeUser(username):
    url = '/Users/New'
    data = {
        'Name': str(username)
    }
    return post(url, None, payload=data)


def deleteUser(userId):
    url = '/Users/{}'.format(str(userId))
    return delete(url, None)


def disableUser(userId, enable=False):
    payload = {
        "IsDisabled": True,
    }
    if enable:
        payload['IsDisabled'] = False
    return updatePolicy(userId, policy=payload)


def resetPassword(userId):
    url = '/Users/{}/Password'.format(userId)
    data = {
        'Id': str(userId),
        'ResetPassword': 'true'
    }
    return postWithToken(hdr=token_header, url=url, data=data)


def setUserPassword(userId, currentPass, newPass):
    url = '/Users/{}/Password'.format(userId)
    data = {
        'Id': userId,
        'CurrentPw': currentPass,
        'NewPw': newPass
    }
    return postWithToken(hdr=token_header, url=url, data=data)


def updatePolicy(userId, policy=None):
    if not policy:
        policy = settings.JELLYFIN_USER_POLICY
    url = '/Users/{}/Policy'.format(userId)
    return postWithToken(hdr=token_header, url=url, data=policy)


def search(keyword, mediaType: str = None, limit: int = None):
    url = '/Search/Hints?{}'.format(urlencode({'SearchTerm': keyword}))
    if mediaType.lower() == 'movie':
        url += '&IncludeItemTypes=Movie'
    elif mediaType.lower() in ['show', 'tv', 'series', 'episode']:
        url += '&IncludeItemTypes=Episode,Series'
    if limit:
        url += f'&limit={str(limit)}'
    return getWithToken(hdr=token_header, url=url)['SearchHints']


def getUserLibraries(user_id=None):
    if not user_id:
        user_id = admin_id
    url = '/Users/{}/Items'.format(str(user_id))
    return getWithToken(hdr=token_header, url=url)


def getAllLibraries():
    return get(cmd='/Library/MediaFolders', params=None)


def getUsers_short():
    url = '/user_usage_stats/user_list'
    return get(url, None)


def getUsers_details():
    url = '/Users'
    return get(url, None)


def getUserDetails(user_id):
    for user in getUsers_details():
        if user['Id'] == user_id:
            return user
    return None


def getUserConfig(user_id):
    try:
        details = getUserDetails(user_id=user_id)
        return details.get('Configuration')
    except Exception as e:
        print(f"{e}")
    return None


def getUserPolicy(user_id):
    try:
        details = getUserDetails(user_id=user_id)
        return details.get('Policy')
    except Exception as e:
        print(f"{e}")
    return None


def getUserDetailsSimplified(user_id):
    try:
        details = getUserDetails(user_id=user_id)
        simplifiedDetails = {
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
                'EnabledDevices': (True if policy.get('EnableAllDevices') == True else policy.get('EnabledDevices')),
                'EnabledChannels': (True if policy.get('EnableAllChannels') == True else policy.get('EnabledChannels')),
                'EnabledFolders': (True if policy.get('EnableAllFolders') == True else policy.get('EnabledFolders')),
                'RemoteBitrateLimit': policy.get('RemoteClientBitrateLimit'),
                'PublicSharing': policy.get('EnablePublicSharing'),
                'InvalidLoginAttempts': policy.get('InvalidLoginAttempts'),
                'InvalidLoginLockout': (False if policy.get('LoginAttemptsBeforeLockout') == -1 else policy.get(
                    'LoginAttemptsBeforeLockout'))
            }
            user_folders = getUserLibraries(user_id=user_id)
            folder_names = []
            if user_folders and user_folders.get('Items'):
                folder_names = [folder['Name'] for folder in user_folders.get('Items')]
            policyDetails['EnabledFolderNames'] = folder_names
            simplifiedDetails.update(policyDetails)
        return simplifiedDetails
    except Exception as e:
        print(f"Error in getUserDetailsSimplified: {e}")
    return None


def updateRating(itemId, upvote, user_id=None):
    if not user_id:
        user_id = admin_id
    url = '/Users/{}/Items/{}/Rating?{}'.format(str(user_id), str(itemId), urlencode({'Likes': upvote}))
    return postWithToken(hdr=token_header, url=url)


def makePlaylist(name):
    url = '/Playlists?{}'.format(urlencode({'Name': name}))
    return postWithToken(hdr=token_header, url=url)


def addToPlaylist(playlistId, itemIds):
    item_list = ','.join(itemIds)
    url = '/Playlists/{}/Items?{}'.format(str(playlistId), str(item_list))
    return postWithToken(hdr=token_header, url=url)


def statsCustomQuery(query):
    url = '/user_usage_stats/submit_custom_query'
    return post(url, None, query).json()


def getStatus():
    return requests.get('{}/swagger'.format(settings.JELLYFIN_URL), timeout=10).status_code


def getServerInfo():
    return get(cmd='/System/Info')


def getAllSessions(params=None):
    return getWithToken(hdr=token_header, url='/Sessions', data=params)


def getLiveSessions():
    live_sessions = []
    sessions = getAllSessions(params={'ActiveWithinSeconds': 20})
    for session in sessions:
        if session.get('NowPlayingItem'):
            live_sessions.append(NowPlayingItem(data=session))
    return live_sessions


def sendPlayStateCommand(session_id, command):
    url = f'/Sessions/{session_id}/Playing/{command}'
    return postWithToken(hdr=token_header, url=url)


def sendMessageToClient(session_id, message):
    url = f'/Sessions/{session_id}/Message'
    return postWithToken(hdr=token_header, url=url, data={'Text': str(message)})


def stopStream(stream_id, message_to_viewer=None):
    if message_to_viewer:
        sendMessageToClient(session_id=stream_id, message=message_to_viewer)
    return sendPlayStateCommand(session_id=stream_id, command='Stop')


def getUsernameFromId(user_id):
    user_list = getUsers_short()
    for user in user_list:
        if user.get('id') == user_id:
            return user.get('name')
    return None


def getUserIdFromUsername(username):
    user_list = getUsers_short()
    for user in user_list:
        if user.get('name') == username:
            return user.get('id')
    return None


def get_defined_libraries():
    nicknames = [name for name in settings.JELLYFIN_LIBRARIES.keys()]
    names = []
    for _, v in settings.JELLYFIN_LIBRARIES.items():
        if v not in names:
            names.append(v)
    return {'Nicknames': nicknames, 'Full Names': names}


def getLibraryNameFromId(library_id):
    libraries = getAllLibraries()
    for lib in libraries['Items']:
        if lib['Id'] == library_id:
            return lib['Name']
    return None


def getLibraryIdFromName(library_name):
    libraries = getAllLibraries()
    for lib in libraries['Items']:
        if lib['Name'] == library_name:
            return lib['Id']
    return None


def get_suggestion_by_user_id(user_id, media="Movie,Episode", limit=1):
    """
    ONLY WORKS FOR CURRENTLY-AUTHENTICATED USER
    """
    return getWithToken(hdr=token_header, url=f"/Users/{user_id}/Suggestions?type={media}&limit={limit}")


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
