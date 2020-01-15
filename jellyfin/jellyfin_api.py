import requests
import socket
import json
from urllib.parse import urlencode
import os

JELLYFIN_URL = os.environ.get('JELLYFIN_URL')
JELLYFIN_API_KEY = os.environ.get('JELLYFIN_API_KEY')
JELLYFIN_ADMIN_USERNAME = os.environ.get('JELLYFIN_ADMIN_USER')
JELLYFIN_ADMIN_PASSWORD = os.environ.get('JELLYFIN_ADMIN_PASS')

JELLYFIN_USER_POLICY = {
    "IsAdministrator": "false",
    "IsHidden": "true",
    "IsHiddenRemotely": "true",
    "IsDisabled": "false",
    "EnableRemoteControlOfOtherUsers": "false",
    "EnableSharedDeviceControl": "false",
    "EnableRemoteAccess": "true",
    "EnableLiveTvManagement": "false",
    "EnableLiveTvAccess": "false",
    "EnableContentDeletion": "false",
    "EnableContentDownloading": "false",
    "EnableSyncTranscoding": "false",
    "EnableSubtitleManagement": "false",
    "EnableAllDevices": "true",
    "EnableAllChannels": "false",
    "EnablePublicSharing": "false",
    "InvalidLoginAttemptCount": 5,
    "BlockedChannels": [
        "IPTV",
        "TVHeadEnd Recordings"
    ]
}

token_header = None
admin_id = None


def authenticate():
    global token_header
    global admin_id
    xEmbyAuth = {
        'X-Emby-Authorization': 'Emby UserId="{UserId}", Client="{Client}", Device="{Device}", DeviceId="{'
                                'DeviceId}", Version="{Version}", Token="""'.format(
            UserId="",  # not required, if it was we would have to first request the UserId from the username
            Client='account-automation',
            Device=socket.gethostname(),
            DeviceId=hash(socket.gethostname()),
            Version=1,
            Token=""  # not required
        )}
    data = {'Username': JELLYFIN_ADMIN_USERNAME, 'Password': JELLYFIN_ADMIN_PASSWORD,
            'Pw': JELLYFIN_ADMIN_PASSWORD}
    try:
        res = postWithToken(hdr=xEmbyAuth, method='/Users/AuthenticateByName', data=data).json()
        token_header = {'X-Emby-Token': '{}'.format(res['AccessToken'])}
        admin_id = res['User']['Id']
    except Exception as e:
        print('Could not log into Jellyfin.\n{}'.format(e))


def get(cmd, params=None):
    return json.loads(requests.get(
        '{}{}?api_key={}{}'.format(JELLYFIN_URL, cmd, JELLYFIN_API_KEY, ("&" + params if params else ""))).text)


def getWithToken(hdr, method, data=None):
    hdr = {'accept': 'application/json', **hdr}
    res = requests.get('{}{}'.format(JELLYFIN_URL, method), headers=hdr, data=json.dumps(data)).json()
    return res


def post(cmd, params, payload):
    return requests.post(
        '{}{}?api_key={}{}'.format(JELLYFIN_URL, cmd, JELLYFIN_API_KEY, ("&" + params if params is not None else "")),
        json=payload)


def postWithToken(hdr, method, data=None):
    hdr = {'accept': 'application/json', 'Content-Type': 'application/json', **hdr}
    res = requests.post('{}{}'.format(JELLYFIN_URL, method), headers=hdr, data=json.dumps(data))
    return res


def delete(cmd, params):
    return requests.delete(
        '{}{}?api_key={}{}'.format(JELLYFIN_URL, cmd, JELLYFIN_API_KEY, ("&" + params if params is not None else "")))


def makeUser(username):
    url = '/Users/New'
    data = {
        'Name': username
    }
    return post(url, None, payload=data)


def deleteUser(userId):
    url = '/Users/{}'.format(str(userId))
    return delete(url, None)


def resetPassword(userId):
    url = '/Users/{}/Password'.format(userId)
    data = {
        'Id': str(userId),
        'ResetPassword': 'true'
    }
    return postWithToken(hdr=token_header, method=url, data=data)


def setUserPassword(userId, currentPass, newPass):
    url = '/Users/{}/Password'.format(userId)
    data = {
        'Id': userId,
        'CurrentPw': currentPass,
        'NewPw': newPass
    }
    return postWithToken(hdr=token_header, method=url, data=data)


def updatePolicy(userId, policy=None):
    if not policy:
        policy = JELLYFIN_USER_POLICY
    url = '/Users/{}/Policy'.format(userId)
    return post(url, None, payload=policy)


def search(keyword):
    url = '/Search/Hints?{}'.format(urlencode({'SearchTerm': keyword}))
    return getWithToken(hdr=token_header, method=url)['SearchHints']


def getLibraries():
    url = '/Users/{}/Items'.format(str(admin_id))
    return getWithToken(hdr=token_header, method=url)


def getUsers():
    url = '/user_usage_stats/user_list'
    return get(url, None)


def updateRating(itemId, upvote):
    url = '/Users/{}/Items/{}/Rating?{}'.format(str(admin_id), str(itemId), urlencode({'Likes': upvote}))
    print(url)
    return postWithToken(hdr=token_header, method=url)


def makePlaylist(name):
    url = '/Playlists?{}'.format(urlencode({'Name': name}))
    print(url)
    return postWithToken(hdr=token_header, method=url)


def addToPlaylist(playlistId, itemIds):
    item_list = ','.join(itemIds)
    url = '/Playlists/{}/Items?{}'.format(str(playlistId), str(item_list))
    print(url)
    return postWithToken(hdr=token_header, method=url)


def statsCustomQuery(query):
    url = '/user_usage_stats/submit_custom_query'
    return post(url, None, query)
