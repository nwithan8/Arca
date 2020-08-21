import requests

endpoints = {
    'post_import_users': '{}/Job/plexuserimporter',
    'get_users': '{}/Identity/Users',
    'delete_user': '{}/Identity/',
    'get_movie_count': '{}/Request/movie/total',
    'post_request_movie': '{}/Request/movie/1/',
    'post_approve_movie': '{}/Request/movie/approve',
    'get_tv_count': '{}/Request/tv/total',
    'post_request_tv': '{}/Request/tv/1/',
    'post_approve_tv': '{}/Request/tv/approve'

}


def _make_endpoint(target_endpoint, append: str = None):
    try:
        return f"{endpoints[target_endpoint]}{(append if append else '')}"
    except:
        pass
    return None


def _get(target_endpoint, headers, append: str = None):
    url = _make_endpoint(target_endpoint=target_endpoint, append=append)
    if url:
        return requests.get(url=url, headers=headers)
    return None


def _delete(target_endpoint, headers, append: str = None):
    url = _make_endpoint(target_endpoint=target_endpoint, append=append)
    if url:
        return requests.delete(url=url, headers=headers)
    return None


def _post(target_endpoint, headers, append: str = None, data=None):
    url = _make_endpoint(target_endpoint=target_endpoint, append=append)
    if url:
        return requests.post(url=url, data=data, headers=headers)
    return None


class OmbiUser:
    def __init__(self, data):
        self.username = data.get('userName')
        self.id = data.get('id')


class OmbiConnector:
    def __init__(self, url: str, api_key: str):
        self.url = f'{url}/api/v1'
        self.headers = {'ApiKey': api_key}
        self.approve_header = {'ApiKey': api_key, 'accept': 'application/json',
                               'Content-Type': 'application/json-patch+json'}

    def get_user(self, username):
        data = _get(target_endpoint='get_users', headers=self.headers)
        if data:
            for user in data.json():
                if user['userName'].lower() == username.lower():
                    return OmbiUser(user)
        return None

    def refresh_users(self):
        return _post(target_endpoint='post_import_users', headers=self.headers)

    def delete_user(self, plex_username):
        user = self.get_user(username=plex_username)
        if user:
            return _delete(target_endpoint='delete_user', append=user.id, headers=self.headers)
        return None
