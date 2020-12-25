# Plex playing settings
TERMINATE_MESSAGE = "Please direct message @Nate in the Discord server."

# Plex watchlist settings
SUBSCRIBER_WATCHLIST_TITLE = "{}'s Watchlist"
SUBSCRIBER_PLAYLIST_TITLE = "{}'s Playlist"

ENABLE_BLACKLIST = True

# Discord settings
DISCORD_SERVER_ID = '472537215457689601'
DISCORD_ADMIN_ID = '233771307555094528'
DISCORD_ADMIN_ROLE_NAME = 'Admin 👑'


# Subscriber settings
INVITED_ROLE = "Invited" # Role given after someone is added to Plex
AUTO_CHECK_SUBS = False
SUB_ROLES = ["Monthly Subscriber 🕒", "Yearly Subscriber 📅", "Winner 🏆", "Lifetime Subscriber ⛰️", "Bot"]  # Users with any of these roles is exempt from removal
EXEMPT_SUBS = [DISCORD_ADMIN_ID]  # Discord IDs for users exempt from subscriber checks/deletion, separated by commas
SUB_CHECK_TIME = 7  # days
CURRENTLY_PLAYING_ROLE_NAME = 'Watching'

# Trial settings
TRIAL_ROLE_NAME = "Trial ⏰"  # Role given to a trial user
TRIAL_LENGTH = 24 * 60 * 60  # (seconds) How long a trial lasts
TRIAL_CHECK_FREQUENCY = 15  # (minutes) How often the bot checks for trial expirations

# Winner settings
WINNER_ROLE_NAME = "Winner 🏆"  # Role given to a winner
WINNER_THRESHOLD = 7200  # (seconds) How long a winner has to use every WEEK to keep access
AUTO_WINNERS = False
# True: Messages from the indicated GIVEAWAY_BOT_ID user will be scanned for mentioned Discord users (winners). The
# winners will be auto-assigned the TEMP_WINNER_ROLE_NAME. That role gives them access to a specified WINNER_CHANNEL
# channel Users then post their Jellyfin username (ONLY their Jellyfin username) in the channel, which is processed
# by the bot. The bot invites the Jellyfin username, and associates the Discord user author of the message with the
# Jellyfin username in the database_handler. The user is then have the TEMP_WINNER_ROLE_NAME role removed (which removes them
# from the WINNER_CHANNEL channel), and assigned the final WINNER_ROLE_NAME role.
TEMP_WINNER_ROLE_NAME = "Uninvited Winner"  # Role temporarily given to a winner (used if AUTO_WINNERS = True)
WINNER_CHANNEL = 0  # Channel ID
GIVEAWAY_BOT_ID = 0  # User ID for the Giveaway Bot that announces contest winners

# Credentials settings
CREDENTIALS_FOLDER = 'media_server/plex/credentials'

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
