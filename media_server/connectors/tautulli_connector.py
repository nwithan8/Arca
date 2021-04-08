from typing import Union, List

from tautulli.api import ObjectAPI

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


class TautulliHomeStats:
    def __init__(self, data):
        self._data = data

    def get_category(self, category_name: str):
        for category in self._data:
            if category.stat_title == category_name:
                return category
        return None


class TautulliWatchTimeStats:
    def __init__(self, data):
        self._data = data

    def get_by_day(self, days: int):
        for stat in self._data:
            if stat.query_days == days:
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
        self.url = url
        self.api = ObjectAPI(base_url=url, api_key=api_key)

    @property
    def users(self):
        return self.api.users

    def get_user_watch_time_stats(self, user_id: str, days: List[int] = None):
        data = self.api.get_user_watch_time_stats(user_id=user_id, query_days=days)
        return TautulliWatchTimeStats(data=data)

    def get_user_ips(self, user_id: str):
        return self.api.get_user_ips(user_id=user_id, order_column='last_seen')

    def get_last_time_user_seen(self, user_id: str) -> int:
        user_ips = self.get_user_ips(user_id=user_id)
        if not user_ips:
            return 0
        return user_ips.data[0].last_seen

    def refresh_users(self) -> bool:
        return self.api.refresh_users_list()

    def delete_user(self, plex_username: str) -> bool:
        return self.api.delete_user(user_id=plex_username)

    # ACTIVITY

    def home_stats(self, time_range: int = 30, stat_category: str = 'user', stat_type: str = 'duration',
                   stat_count: int = 5) -> Union[TautulliHomeStats, None]:
        category_number = _stat_category_to_number(stat_category=stat_category)
        if not category_number:
            return None

        data = self.api.get_home_stats(time_range=time_range, stats_type=stat_type, stat_count=stat_count)
        return TautulliHomeStats(data=data)

    @property
    def current_activity(self):
        return self.api.activity

    # MEDIA

    @property
    def libraries(self):
        return self.api.libraries

    def get_library_media_info(self, section_id: str):
        return self.api.get_library_media_info(section_id=section_id)

    def recently_added(self, count: int = 5):
        return self.api.get_recently_added(count=count)

    def image_thumb_url(self, thumb: str) -> str:
        if self.api.pms_image_proxy(img=thumb):
            return f'{self.url}&cmd=pms_image_proxy&img={thumb}'

    def delete_image_cache(self) -> bool:
        return self.api.delete_image_cache()

    def search(self, keyword: str):
        return self.api.search(query=keyword)

    # SESSIONS

    def terminate_session(self, session_id, message: str = None) -> bool:
        return self.api.terminate_session(session_id=session_id, message=message)
