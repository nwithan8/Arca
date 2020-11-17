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
    'post_approve_tv': '{}/Request/tv/approve',
    'post_notification_preferences': '{}/Identity/NotificationPreferences'
}


def _make_notification_body(notifier_number: int, notifier_value, user_id: str):
    return {
        'agent': notifier_number,
        'userId': user_id,
        'value': str(notifier_value),
        'enabled': True
    }


class OmbiUser:
    def __init__(self, data):
        self.username = data.get('userName')
        self.id = data.get('id')
        self.alias = data.get('alias')
        self.email = data.get('emailAddress')
        self.password = data.get('password')
        self.userType = data.get('userType')


class OmbiConnector:
    def __init__(self, url: str, api_key: str):
        self.url = f'{url}/api/v1'
        self.headers = {'ApiKey': api_key}
        self.approve_header = {'ApiKey': api_key, 'accept': 'application/json',
                               'Content-Type': 'application/json-patch+json'}

    def _make_endpoint(self, target_endpoint, append: str = None):
        try:
            return f"{endpoints[target_endpoint].format(self.url)}{(append if append else '')}"
        except:
            return None

    def _get(self, target_endpoint, headers, append: str = None):
        url = self._make_endpoint(target_endpoint=target_endpoint, append=append)
        if url:
            return requests.get(url=url, headers=headers)
        return None

    def _delete(self, target_endpoint, headers, append: str = None):
        url = self._make_endpoint(target_endpoint=target_endpoint, append=append)
        if url:
            return requests.delete(url=url, headers=headers)
        return None

    def _post(self, target_endpoint, headers, append: str = None, data=None):
        url = self._make_endpoint(target_endpoint=target_endpoint, append=append)
        if url:
            return requests.post(url=url, data=data, headers=headers)
        return None

    def get_user(self, username):
        data = self._get(target_endpoint='get_users', headers=self.headers)
        if data:
            for user in data.json():
                if user['userName'].lower() == username.lower():
                    return OmbiUser(user)
        return None

    def refresh_users(self):
        if self._post(target_endpoint='post_import_users', headers=self.headers):
            return True
        return False

    def delete_user(self, plex_username):
        user = self.get_user(username=plex_username)
        if user:
            return self._delete(target_endpoint='delete_user', append=user.id, headers=self.headers)
        return None

    def add_discord_id(self, discord_id: int, ombi_username: str = None, ombi_user_id: str = None):
        if not ombi_username and not ombi_user_id:
            raise Exception("Must provide either Ombi username or Ombi user ID")
        if not ombi_user_id:
            try:
                ombi_user_id = self.get_user(username=ombi_username).id
            except:
                raise Exception(f"Could not locate an Ombi user with the username: {ombi_username}")
        body = _make_notification_body(notifier_number=1,
                                       notifier_value=discord_id,
                                       user_id=ombi_user_id)
        if self._post(target_endpoint='post_notification_preferences', data=body, headers=self.headers):
            return True
        return False
