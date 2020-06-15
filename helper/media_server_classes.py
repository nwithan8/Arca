import json
import os


class PlexConfig:
    def __init__(self, config_file):
        with open(config_file) as f:
            data = json.load(f)
            self.data = data
            self.PLEX_SERVER_URLS = data.get('PLEX_SERVER_URLS')
            self.PLEX_SERVER_TOKENS = data.get('PLEX_SERVER_TOKENS')
            self.PLEX_SERVER_IDS = data.get('PLEX_SERVER_IDS')
            self.PLEX_SERVER_NAMES = data.get('PLEX_SERVER_NAMES')
            self.PLEX_SERVER_ALT_NAMES = data.get('PLEX_SERVER_ALT_NAMES')
            self.MULTI_PLEX = data.get('MULTI_PLEX')
            self.PLEX_LIBRARIES = data.get('PLEX_LIBRARIES')
            self.TERMINATE_MESSAGE = data.get('TERMINATE_MESSAGE')
            self.SUBSCRIBER_WATCHLIST_TITLE = data.get('SUBSCRIBER_WATCHLIST_TITLE')
            self.SUBSCRIBER_PLAYLIST_TITLE = data.get('SUBSCRIBER_PLAYLIST_TITLE')
            self.USE_TAUTULLI = data.get('USE_TAUTULLI')
            self.TAUTULLI_URLS = data.get('TAUTULLI_URLS')
            self.TAUTULLI_API_KEYS = data.get('TAUTULLI_API_KEYS')
            self.MULTI_TAUTULLI = data.get('MULTI_TAUTULLI')
            self.USE_OMBI = data.get('USE_OMBI')
            self.OMBI_URL = data.get('OMBI_URL')
            self.OMBI_API_KEY = data.get('OMBI_API_KEY')
            self.DISCORD_CONNECTOR_FILE = data.get('DISCORD_CONNECTOR_FILE')
            self.ENABLE_BLACKLIST = data.get('ENABLE_BLACKLIST')
            self.USE_DROPBOX = data.get('USE_DROPBOX')
            self.DISCORD_SERVER_ID = data.get('DISCORD_SERVER_ID')
            self.DISCORD_ADMIN_ID = data.get('DISCORD_ADMIN_ID')
            self.DISCORD_ADMIN_ROLE_NAME = data.get('DISCORD_ADMIN_ROLE_NAME')
            self.AFTER_APPROVED_ROLE_NAME = data.get('AFTER_APPROVED_ROLE_NAME')
            self.AUTO_CHECK_SUBS = data.get('AUTO_CHECK_SUBS')
            self.SUB_ROLES = data.get('SUB_ROLES')
            self.EXEMPT_IDS = data.get('EXEMPT_IDS')
            self.SUB_CHECK_TIME = data.get('SUB_CHECK_TIME')
            self.CURRENTLY_PLAYING_ROLE_NAME = data.get('CURRENTLY_PLAYING_ROLE_NAME')
            self.TRIAL_ROLE_NAME = data.get('TRAIL_ROLE_NAME')
            self.TRIAL_LENGTH = data.get('TRIAL_LENGTH')
            self.TRIAL_CHECK_FREQUENCY = data.get('TRIAL_CHECK_FREQUENCY')
            self.WINNER_ROLE_NAME = data.get('WINNER_ROLE_NAME')
            self.WINNER_THRESHOLD = data.get('WINNER_THRESHOLD')
            self.AUTO_WINNERS = data.get('AUTO_WINNERS')
            self.TEMP_WINNER_ROLE_NAME = data.get('TEMP_WINNER_ROLE_NAME')
            self.WINNER_CHANNEL_ID = data.get('WINNER_CHANNEL_ID')
            self.GIVEAWAY_BOT_ID = data.get('GIVEAWAY_BOT_ID')
            self.CREDENTIALS_FOLDER = data.get('CREDENTIALS_FOLDER')
            self.PLEX_RECS_LIBRARIES = data.get('PLEX_RECS_LIBRARIES')
            self.YOUTUBE_API_KEY = data.get('YOUTUBE_API_KEY')


class JellyfinConfig:
    def __init__(self, config_file):
        with open(config_file) as f:
            data = json.load(f)
            self.data = data
            self.JELLYFIN_URL = data.get('JELLYFIN_URL')
            self.JELLYFIN_API_KEY = data.get('JELLYFIN_API_KEY')
            self.JELLYFIN_ADMIN_USERNAME = data.get('JELLYFIN_ADMIN_USERNAME')
            self.JELLYFIN_ADMIN_PASSWORD = data.get('JELLYFIN_ADMIN_PASSWORD')
            self.JELLYFIN_SERVER_NICKNAME = data.get('JELLYFIN_SERVER_NICKNAME')
            self.JELLYFIN_USER_POLICY = data.get('JELLYFIN_USER_POLICY')
            self.JELLYFIN_LIBRARIES = data.get('JELLYFIN_LIBRARIES')
            self.DISCORD_CONNECTOR_FILE = data.get('DISCORD_CONNECTOR_FILE')
            self.ENABLE_BLACKLIST = data.get('ENABLE_BLACKLIST')
            self.USE_DROPBOX = data.get('USE_DROPBOX')
            self.DISCORD_SERVER_ID = data.get('DISCORD_SERVER_ID')
            self.DISCORD_ADMIN_ID = data.get('DISCORD_ADMIN_ID')
            self.DISCORD_ADMIN_ROLE_NAME = data.get('DISCORD_ADMIN_ROLE_NAME')
            self.AFTER_APPROVED_ROLE_NAME = data.get('AFTER_APPROVED_ROLE_NAME')
            self.AUTO_CHECK_SUBS = data.get('AUTO_CHECK_SUBS')
            self.SUB_ROLES = data.get('SUB_ROLES')
            self.EXEMPT_IDS = data.get('EXEMPT_IDS')
            self.SUB_CHECK_TIME = data.get('SUB_CHECK_TIME')
            self.CURRENTLY_PLAYING_ROLE_NAME = data.get('CURRENTLY_PLAYING_ROLE_NAME')
            self.TRIAL_ROLE_NAME = data.get('TRAIL_ROLE_NAME')
            self.TRIAL_LENGTH = data.get('TRIAL_LENGTH')
            self.TRIAL_CHECK_FREQUENCY = data.get('TRIAL_CHECK_FREQUENCY')
            self.TRIAL_END_NOTIFICATION = data.get('TRIAL_END_NOTIFICATION')
            self.WINNER_ROLE_NAME = data.get('WINNER_ROLE_NAME')
            self.WINNER_THRESHOLD = data.get('WINNER_THRESHOLD')
            self.AUTO_WINNERS = data.get('AUTO_WINNERS')
            self.TEMP_WINNER_ROLE_NAME = data.get('TEMP_WINNER_ROLE_NAME')
            self.WINNER_CHANNEL_ID = data.get('WINNER_CHANNEL_ID')
            self.GIVEAWAY_BOT_ID = data.get('GIVEAWAY_BOT_ID')
            self.CREATE_PASSWORD = data.get('CREATE_PASSWORD')
            self.NO_PASSWORD_MESSAGE = data.get('NO_PASSWORD_MESSAGE')
            self.USE_PASTEBIN = data.get('USE_PASTEBIN')
            self.PRIVATEBIN_URL = data.get('PRIVATEBIN_URL')
            self.HASTEBIN_URL = data.get('HASTEBIN_URL')
            self.MIGRATION_FILE = data.get('MIGRATION_FILE')
            self.YOUTUBE_API_KEY = data.get('YOUTUBE_API_KEY')


class EmbyConfig:
    def __init__(self, config_file):
        with open(config_file) as f:
            data = json.load(f)
            self.data = data
            self.EMBY_URL = data.get('EMBY_URL')
            self.EMBY_API_KEY = data.get('EMBY_API_KEY')
            self.EMBY_ADMIN_USERNAME = data.get('EMBY_ADMIN_USERNAME')
            self.EMBY_ADMIN_PASSWORD = data.get('EMBY_ADMIN_PASSWORD')
            self.EMBY_SERVER_NICKNAME = data.get('EMBY_SERVER_NICKNAME')
            self.EMBY_USER_POLICY = data.get('EMBY_USER_POLICY')
            self.EMBY_LIBRARIES = data.get('EMBY_LIBRARIES')
            self.DISCORD_CONNECTOR_FILE = data.get('DISCORD_CONNECTOR_FILE')
            self.ENABLE_BLACKLIST = data.get('ENABLE_BLACKLIST')
            self.USE_DROPBOX = data.get('USE_DROPBOX')
            self.DISCORD_SERVER_ID = data.get('DISCORD_SERVER_ID')
            self.DISCORD_ADMIN_ID = data.get('DISCORD_ADMIN_ID')
            self.DISCORD_ADMIN_ROLE_NAME = data.get('DISCORD_ADMIN_ROLE_NAME')
            self.AFTER_APPROVED_ROLE_NAME = data.get('AFTER_APPROVED_ROLE_NAME')
            self.AUTO_CHECK_SUBS = data.get('AUTO_CHECK_SUBS')
            self.SUB_ROLES = data.get('SUB_ROLES')
            self.EXEMPT_IDS = data.get('EXEMPT_IDS')
            self.SUB_CHECK_TIME = data.get('SUB_CHECK_TIME')
            self.CURRENTLY_PLAYING_ROLE_NAME = data.get('CURRENTLY_PLAYING_ROLE_NAME')
            self.TRIAL_ROLE_NAME = data.get('TRAIL_ROLE_NAME')
            self.TRIAL_LENGTH = data.get('TRIAL_LENGTH')
            self.TRIAL_CHECK_FREQUENCY = data.get('TRIAL_CHECK_FREQUENCY')
            self.TRIAL_END_NOTIFICATION = data.get('TRIAL_END_NOTIFICATION')
            self.WINNER_ROLE_NAME = data.get('WINNER_ROLE_NAME')
            self.WINNER_THRESHOLD = data.get('WINNER_THRESHOLD')
            self.AUTO_WINNERS = data.get('AUTO_WINNERS')
            self.TEMP_WINNER_ROLE_NAME = data.get('TEMP_WINNER_ROLE_NAME')
            self.WINNER_CHANNEL_ID = data.get('WINNER_CHANNEL_ID')
            self.GIVEAWAY_BOT_ID = data.get('GIVEAWAY_BOT_ID')
            self.CREATE_PASSWORD = data.get('CREATE_PASSWORD')
            self.NO_PASSWORD_MESSAGE = data.get('NO_PASSWORD_MESSAGE')
            self.USE_PASTEBIN = data.get('USE_PASTEBIN')
            self.PRIVATEBIN_URL = data.get('PRIVATEBIN_URL')
            self.HASTEBIN_URL = data.get('HASTEBIN_URL')
            self.MIGRATION_FILE = data.get('MIGRATION_FILE')
            self.YOUTUBE_API_KEY = data.get('YOUTUBE_API_KEY')


def get_config(server_type, path_to_settings=None):
    if not path_to_settings:
        path_to_settings = f'media_server/{server_type}/settings.json.priv'
    if server_type == 'plex':
        return PlexConfig(config_file=path_to_settings)
    elif server_type == 'jellyfin':
        return JellyfinConfig(config_file=path_to_settings)
    elif server_type == 'emby':
        return EmbyConfig(config_file=path_to_settings)
    else:
        print("Error in get_config")
    return None
