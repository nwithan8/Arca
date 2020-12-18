from decimal import Decimal

import requests
from urllib.parse import urlencode
from typing import Union
from helper.utils import humanbitrate
from helper.discord_helper import emoji_numbers

sessions_message = """{stream_count} stream{plural}"""
transcodes_message = """{transcode_count} transcode{plural}"""
bandwidth_message = """🌐 {bandwidth}"""
lan_bandwidth_message = """(🏠 {bandwidth})"""

session_title_message = """{count}—{icon}-{media_type_icon}-{username}: *{title}*"""
session_player_message = """__Player__: {product} ({player})"""
session_details_message = """__Quality__: {quality_profile} ({bandwidth}){transcoding}"""

status_icons = {
        "playing": "▶️",
        "paused": "⏸",
        "stopped": "⏹",
        "buffering": "⏳",
        "error": "⚠️"
}

def build_overview_message(stream_count=0, transcode_count=0, total_bandwidth=0, lan_bandwidth=0):
    overview_message = ""
    if int(stream_count) > 0:
        overview_message += sessions_message.format(stream_count=stream_count,
                                                    plural=('s' if int(stream_count) > 1 else ''))
    if transcode_count > 0:
        overview_message += f" ({transcodes_message.format(transcode_count=transcode_count, plural=('s' if int(transcode_count) > 1 else ''))})"
    if total_bandwidth > 0:
        overview_message += f" | {bandwidth_message.format(bandwidth=humanbitrate(float(total_bandwidth)))}"
        if lan_bandwidth > 0:
            overview_message += f" {lan_bandwidth_message.format(bandwidth=humanbitrate(float(lan_bandwidth)))}"
    return overview_message


def build_stream_message(session_data,
                         count: int = 0,
                         state: str = "",
                         username: str = "",
                         title: str = "",
                         product: str = "",
                         player: str = "",
                         quality_profile: str = "",
                         bandwidth: str = "0",
                         stream_container_decision: str = "",
                         auto_decode: bool = False):
    if auto_decode:
        state = session_data.get('state')
        username = session_data.get('username')
        title = session_data.get('full_title')
        product = session_data.get('product')
        player = session_data.get('player')
        quality_profile = session_data.get('quality_profile')
        bandwidth = session_data.get('bandwidth')
        stream_container_decision = session_data.get('stream_container_decision')
    if session_data['media_type'] == 'episode':
        title = f"{session_data.get('grandparent_title', '')} - S{session_data.get('parent_title', '').replace('Season ', '').zfill(2)}E{session_data.get('media_index', '').zfill(2)} - {session_data['title']}"
    media_type_icons = {'episode': '📺', 'track': '🎧', 'movie': '🎞', 'clip': '🎬', 'photo': '🖼'}
    if session_data['media_type'] in media_type_icons:
        media_type_icon = media_type_icons[session_data['media_type']]
    else:
        media_type_icon = '🎁'
    return f"{session_title_message.format(count=emoji_numbers[count - 1], icon=selectIcon(state=state), username=username, media_type_icon=media_type_icon, title=title)}\n" \
           f"{session_player_message.format(product=product, player=player)}\n" \
           f"{session_details_message.format(quality_profile=quality_profile, bandwidth=(humanbitrate(float(bandwidth)) if bandwidth != '' else '0'), transcoding=(' (Transcode)' if stream_container_decision == 'transcode' else ''))}"


def selectIcon(state):
    return status_icons.get(state, "")

class TautulliConnector:
    def __init__(self, url, api_key):
        if url.endswith("/"):
            url = url[:-1]
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
            return None

    def _get_json(self, command, params=None) -> Union[dict, None]:
        try:
            return self._get(command=command, params=params).json()
        except:
            return None

    def refresh_users(self) -> bool:
        if self._get(command='refresh_users_list'):
            return True
        return False

    def delete_user(self, plex_username) -> bool:
        if self._get(command='delete_user', params={'user_id': plex_username}):
            return True
        return False

    def _stat_category_to_number(self, stat_category):
        translations = {
            'movies': 0,
            'shows': 1,
            'artists': 2,
            'users': 7
        }
        return translations.get(stat_category, None)

    def home_stats(self, time_range: int = 30, stat_category: str = 'user', stat_type: str = 'duration', stat_count: int = 5):
        category_number = self._stat_category_to_number(stat_category=stat_category)
        if not category_number:
            return None
        params = {'time_range': time_range,
                  'stats_type': stat_type,
                  'stats_count': stat_count}
        json_data = self._get_json(command='get_home_stats', params=params)
        if json_data:
            return json_data['response']['data'][category_number]['rows']
        return {}

    def current_activity(self, remove_response: bool = False):
        json_data = self._get_json(command="get_activity")
        if json_data:
            if remove_response:
                return json_data['response']['data']
            return json_data
        return {}

    def get_libraries(self, remove_response: bool = False):
        json_data = self._get_json(command="get_libraries")
        if json_data:
            if remove_response:
                return json_data['response']['data']
            return json_data
        return {}

    def get_library_media_info(self, section_id: str, remove_response: bool = False):
        json_data = self._get_json(command='get_library_media_info', params={'section_id': section_id})
        if json_data:
            if remove_response:
                return json_data['response']['data']
            return json_data
        return {}

    def recently_added(self, count: int = 5, remove_response: bool = False):
        json_data = self._get_json(command='get_recently_added', params={'count': count})
        if json_data:
            if remove_response:
                return json_data['response']['data']
            return json_data
        return {}

    def image_thumb_url(self, thumb):
        return f'{self.url}&cmd=pms_image_proxy&img={thumb}'

    def delete_image_cache(self):
        if self._get(command='delete_image_cache'):
            return True
        return False

    def terminate_session(self, session_id, message=None):
        params = {'session_id': session_id}
        if message:
            params['message'] = message
        if self._get(command='terminate_session', params=params):
            return True
        return False

    def search(self, keyword, remove_response: bool = False):
        json_data = self._get_json(command='search', params={'query': keyword})
        if json_data:
            if remove_response:
                return json_data['response']['data']
            return json_data
        return {}

    def get_user_names(self, remove_response: bool = False):
        json_data = self._get_json(command='get_user_names')
        if json_data:
            if remove_response:
                return json_data['response']['data']
            return json_data
        return {}

    def get_user_watch_time_stats(self, user_id, remove_response: bool = False):
        json_data = self._get_json(command="get_user_watch_time_stats", params={'user_id': user_id})
        if json_data:
            if remove_response:
                return json_data['response']['data']
            return json_data
        return {}
