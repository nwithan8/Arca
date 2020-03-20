import os

# Jellyfin settings
JELLYFIN_URL = ''
JELLYFIN_API_KEY = ''
JELLYFIN_ADMIN_USERNAME = ''
JELLYFIN_ADMIN_PASSWORD = ''
JELLYFIN_SERVER_NICKNAME = ''
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

# Discord-to-Jellyfin database (SQLite3)
SQLITE_FILE = 'media_server/jellyfin/JellyfinDiscord.db'  # File path + name + extension (i.e. "/root/nwithan8-cogs/jellyfin_manager/JellyfinDiscord.db"
'''
Database schema:
JellyfinDiscord.users
0|DiscordID|VARCHAR(100)|1||0
1|JellyfinUsername|VARCHAR(100)|0||0
2|JellyfinID|VARCHAR(200)|1||0
3|ExpirationStamp|INT(11)|0||0
4|Note|VARCHAR(5)|0||0
'''
ENABLE_BLACKLIST = True
BLACKLIST_FILE = 'media_server/blacklist.db'

USE_DROPBOX = True  # Store database in Dropbox, download and upload dynamically

# Discord settings
DISCORD_SERVER_ID = ''
DISCORD_ADMIN_ID = ''  # Presumably you, or whoever is the administrator of the Discord server
DISCORD_ADMIN_ROLE_NAME = "Admin"  # Only users with this role can call most administrative commands
AFTER_APPROVED_ROLE_NAME = "Invited"  # Role given after someone is added to Jellyfin

AUTO_CHECK_SUBS = False
SUB_ROLES = ["Monthly Subscriber", "Yearly Subscriber", "Winner", "Bot"]  # Users with any of these roles is exempt from removal
EXEMPT_SUBS = [DISCORD_ADMIN_ID]  # Discord IDs for users exempt from subscriber checks/deletion, separated by commas
SUB_CHECK_TIME = 7  # days

# Trial settings
TRIAL_ROLE_NAME = "Trial Member"  # Role given to a trial user
TRIAL_LENGTH = 24  # (hours) How long a trial lasts
TRIAL_CHECK_FREQUENCY = 15  # (minutes) How often the bot checks for trial expirations
TRIAL_END_NOTIFICATION = "Hello, your {}-hour trial of {} has ended.".format(str(TRIAL_LENGTH),
                                                                             str(JELLYFIN_SERVER_NICKNAME))

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
CREATE_PASSWORD = True  # Create a random password for new Jellyfin users (or else, keep a blank password)
NO_PASSWORD_MESSAGE = "Leave password blank on first login, but please secure your account by setting a password."
USE_PASTEBIN = None  # 'privatebin', 'hastebin' or None
PRIVATEBIN_URL = ''
HASTEBIN_URL = ''

# Migrate/mass import users
MIGRATION_FILE = "/"  # file path + name (leave off ".csv" extension)
