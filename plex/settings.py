import os

# Plex settings
PLEX_SERVER_URL = []
PLEX_SERVER_TOKEN = []
PLEX_SERVER_ID = []  # after "/server/" in browser UI URL
PLEX_SERVER_NAME = []
PLEX_SERVER_ALT_NAME = []
MULTI_PLEX = False

# Plex Recs settings
# http://[PMS_IP_Address]:32400/library/sections?X-Plex-Token=YourTokenGoesHere
# Use the above link to find the number for each library: composite="/library/sections/NUMBER/composite/..."
MOVIE_LIBRARY = 1  # Might be different for your Plex library
TV_LIBRARY = 2  # Might be different for your Plex library
MOVIE_LIBRARY_NAME = 'Movies'
TV_SHOW_LIBRARY_NAME = 'TV Shows'

# Plex playing settings
TERMINATE_MESSAGE = "Please direct message @Nate in the Discord server."

# Plex watchlist settings
SUBSCRIBER_WATCHLIST_TITLE = "{}'s Watchlist"
SUBSCRIBER_PLAYLIST_TITLE = "{}'s Playlist"

# Tautulli settings
USE_TAUTULLI = True
TAUTULLI_URL = []
TAUTULLI_API_KEY = []
MULTI_TAUTULLI = False

# Ombi settings
USE_OMBI = True
OMBI_URL = ''
OMBI_API_KEY = ''

# Discord-to-Plex database (SQLite3)
SQLITE_FILE = 'plex/PlexDiscord.db'  # File path + name + extension (i.e."/root/nwithan8-cogs/plex_manager/PlexDiscord.db"
# Database Schema:
# PlexDiscord.users
# (DiscordID BIGINT, PlexUsername 'VARCHAR(100)', PlexEmail 'VARCHAR(320)', ServerNum INT, ExpirationStamp INT, Note 'VARCHAR(5)')

# Discord settings
DISCORD_SERVER_ID = ''
DISCORD_ADMIN_ID = ''
DISCORD_ADMIN_ROLE_NAME = ''
AFTER_APPROVED_ROLE_NAME = ''  # Role given after someone is added to Plex
SUB_ROLES = ["Monthly Subscriber", "Yearly Subscriber", "Winner", "Bot"]  # Users with any of these roles is exempt from removal
EXEMPT_SUBS = [DISCORD_ADMIN_ID]  # Discord IDs for users exempt from subscriber checks/deletion, separated by commas
SUB_CHECK_TIME = 7  # days
CURRENTLY_PLAYING_ROLE_NAME = 'Watching'

# Trial settings
TRIAL_ROLE_NAME = "Trial Member"  # Role given to a trial user
TRIAL_LENGTH = 24  # (hours) How long a trial lasts
TRIAL_CHECK_FREQUENCY = 15  # (minutes) How often the bot checks for trial expirations

# Winner settings
WINNER_ROLE_NAME = "Winner"  # Role given to a winner
WINNER_THRESHOLD = 7200  # (seconds) How long a winner has to use every WEEK to keep access
AUTO_WINNERS = False
# True: Messages from the indicated GIVEAWAY_BOT_ID user will be scanned for mentioned Discord users (winners). The
# winners will be auto-assigned the TEMP_WINNER_ROLE_NAME. That role gives them access to a specified WINNER_CHANNEL
# channel Users then post their Jellyfin username (ONLY their Jellyfin username) in the channel, which is processed
# by the bot. The bot invites the Jellyfin username, and associates the Discord user author of the message with the
# Jellyfin username in the database. The user is then have the TEMP_WINNER_ROLE_NAME role removed (which removes them
# from the WINNER_CHANNEL channel), and assigned the final WINNER_ROLE_NAME role.
TEMP_WINNER_ROLE_NAME = "Uninvited Winner"  # Role temporarily given to a winner (used if AUTO_WINNERS = True)
WINNER_CHANNEL = 0  # Channel ID
GIVEAWAY_BOT_ID = 0  # User ID for the Giveaway Bot that announces contest winners

# Credentials settings
CREDENTIALS_FOLDER = 'plex/credentials'

# Plex Recs settings
# ex. 'oneWordLowercaseNicknameForGroup': [libraryNumber, libraryNumber]
# Separate each group listing by a , like below
PLEX_RECS_LIBRARIES = {
    'movie': [1],
    'show': [2],
    'artist': [3, 6],
    '4kmovie': [4]
}
YOUTUBE_API_KEY = 'AIzaSyB4DdmAkhKtJ6NMgSJIgMCFkVJ8KD1uBk0'