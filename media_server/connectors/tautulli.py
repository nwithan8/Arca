import requests
from urllib.parse import urlencode
from typing import Union


class TautulliConnector:
    def __init__(self, url, api_key):
        self.url = f"{url}/api/v2?apikey={api_key}"

    def _create_url(self, command, params=None):
        url = f"{self.url}&cmd={command}"
        if params:
            url += f"&{urlencode(params)}"
        return url

    def _get(self, command, params=None) -> Union[requests.Response, None]:
        try:
            url = self._create_url(command=command, params=params)
            return requests.get(url=url)
        except:
            pass
        return None

    def _get_json(self, command, params=None):
        try:
            return self._get(command=command, params=params).json()
        except:
            pass
        return None

    def refresh_users(self):
        if self._get(command='refresh_users_list'):
            return True
        return False

    def delete_user(self, plex_username):
        if self._get(command='delete_user', params={'user_id': plex_username}):
            return True
        return False
