from decimal import Decimal

import requests
from urllib.parse import urlencode
from typing import Union, List
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
    return f"{session_title_message.format(count=emoji_numbers[count - 1], icon=select_icon(state=state), username=username, media_type_icon=media_type_icon, title=title)}\n" \
           f"{session_player_message.format(product=product, player=player)}\n" \
           f"{session_details_message.format(quality_profile=quality_profile, bandwidth=(humanbitrate(float(bandwidth)) if bandwidth != '' else '0'), transcoding=(' (Transcode)' if stream_container_decision == 'transcode' else ''))}"


def select_icon(state):
    return status_icons.get(state, "")


def _stat_category_to_number(stat_category: str) -> Union[int, None]:
    translations = {
        'movies': 0,
        'shows': 1,
        'artists': 2,
        'users': 7
    }
    return translations.get(stat_category, None)

class TautulliHomeStatsCategory:
    def __init__(self, data: dict):
        self._data = data
        self.name = data.get('stat_id')
        self.type = data.get('stat_type')
        self.rows = data.get('rows')


class TautulliHomeStats:
    def __init__(self, data: dict):
        self._data = data
        self.stats = [TautulliHomeStatsCategory(data=category) for category in data]

    def get_category(self, category_name: str) -> Union[TautulliHomeStatsCategory, None]:
        for category in self.stats:
            if category.name == category_name:
                return category
        return None


class TautulliWatchTimeStat:
    def __init__(self, data: dict):
        self._data = data
        self.days = data.get('query_days')
        self.plays = data.get('total_plays')
        self.time = data.get('total_time')


class TautulliWatchTimeStats:
    def __init__(self, data: dict):
        self._data = data
        self.stats = [TautulliWatchTimeStat(data=stat) for stat in data]

    def get_by_day(self, days: int) -> Union[TautulliWatchTimeStat, None]:
        for stat in self.stats:
            if stat.days == days:
                return stat
        return None


class TautulliUser:
    def __init__(self, data: dict, api):
        self._data = data
        self._api = api
        self.username = data.get('username')
        self.id = data.get('user_id')
        self.shared_libraries = data.get('shared_libraries').split(";")


class TautulliConnector:
    def __init__(self, url: str, api_key: str):
        if url.endswith("/"):
            url = url[:-1]
        self.url = f"{url}/api/v2?apikey={api_key}"

    def _create_url(self, command, params=None) -> str:
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



    # USERS

    @property
    def users(self) -> List[TautulliUser]:
        json_data = self._get_json(command='get_users')
        if json_data:
            return [TautulliUser(data=user, api=self) for user in json_data['response']['data']]
        return []

    def get_user_watch_time_stats(self, user_id: str, days: List[int] = None) -> Union[TautulliWatchTimeStats, None]:
        params = {'user_id': user_id}
        if days:
            params['query_days'] = ','.join(map(str, days))
        json_data = self._get_json(command="get_user_watch_time_stats", params=params)
        if json_data:
            return TautulliWatchTimeStats(data=json_data['response']['data'])
        return None

    def get_user_ips(self, user_id: str) -> dict:
        json_data = self._get_json(command='get_user_ips', params={'user_id': user_id, 'order_column': 'last_seen'})
        if json_data:
            return json_data['response']['data']
        return {}

    def get_last_time_user_seen(self, user_id: str) -> int:
        user_ips = self.get_user_ips(user_id=user_id)
        if not user_ips:
            return 0
        return user_ips[0]['last_seen']

    def refresh_users(self) -> bool:
        if self._get(command='refresh_users_list'):
            return True
        return False

    def delete_user(self, plex_username: str) -> bool:
        if self._get(command='delete_user', params={'user_id': plex_username}):
            return True
        return False


    # ACTIVITY

    def home_stats(self, time_range: int = 30, stat_category: str = 'user', stat_type: str = 'duration', stat_count: int = 5) -> Union[TautulliHomeStats, None]:
        category_number = _stat_category_to_number(stat_category=stat_category)
        if not category_number:
            return None
        params = {'time_range': time_range,
                  'stats_type': stat_type,
                  'stats_count': stat_count}
        json_data = self._get_json(command='get_home_stats', params=params)
        if json_data:
            return TautulliHomeStats(data=json_data['response']['data'])
        return None

    @property
    def current_activity(self) -> dict:
        json_data = self._get_json(command="get_activity")
        if json_data:
            return json_data['response']['data']
        return {}


    # MEDIA

    @property
    def libraries(self) -> dict:
        json_data = self._get_json(command="get_libraries")
        if json_data:
            return json_data['response']['data']
        return {}

    def get_library_media_info(self, section_id: str) -> dict:
        json_data = self._get_json(command='get_library_media_info', params={'section_id': section_id})
        if json_data:
            return json_data['response']['data']
        return {}

    def recently_added(self, count: int = 5) -> dict:
        json_data = self._get_json(command='get_recently_added', params={'count': count})
        if json_data:
            return json_data['response']['data']
        return {}

    def image_thumb_url(self, thumb: str) -> str:
        return f'{self.url}&cmd=pms_image_proxy&img={thumb}'

    def delete_image_cache(self) -> bool:
        if self._get(command='delete_image_cache'):
            return True
        return False

    def search(self, keyword: str) -> dict:
        json_data = self._get_json(command='search', params={'query': keyword})
        if json_data:
            return json_data['response']['data']
        return {}


    # SESSIONS

    def terminate_session(self, session_id, message: str = None) -> bool:
        params = {'session_id': session_id}
        if message:
            params['message'] = message
        if self._get(command='terminate_session', params=params):
            return True
        return False
