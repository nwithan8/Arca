from database.tools import *


class MediaServerSettings(Base):
    __tablename__ = "media_server_settings"
    DiscordServerID = Column(Integer, primary_key=True)
    InvitedRoleName = Column(String)
    CurrentlyWatchingRoleName = Column(String)

    AutoCheckSubs = Column(Boolean)
    SubCheckFrequencyDays = Column(Integer)

    TrialRoleName = Column(String)
    AutoCheckTrials = Column(Boolean)
    TrialLengthMinutes = Column(Integer)
    TrialCheckFrequencyMinutes = Column(Integer)

    WinnerRoleName = Column(String)
    AutoCheckWinners = Column(Boolean)
    WinnerWatchTimeThresholdMinutes = Column(Integer)
    WinnerCheckFrequencyDays = Column(Integer)

    WatchlistTemplate = Column(String)
    PlaylistTemplate = Column(String)

    @none_as_null
    def __init__(self,
                 discord_id: int,
                 invited_role_name: str = None,
                 currently_watching_role_name: str = None,
                 auto_check_subs: bool = False,
                 sub_check_frequency_days: int = None,
                 trial_role_name: str = None,
                 auto_check_trials: bool = False,
                 trial_length_minutes: int = None,
                 trial_check_frequency_minutes: int = None,
                 winner_role_name: str = None,
                 auto_check_winners: bool = False,
                 winner_watch_time_threshold_minutes: int = None,
                 winner_check_frequency_days: int = None,
                 watchlist_template: str = "{}'s Watchlist",
                 playlist_template: str = "{}'s Playlist"):
        self.DiscordServerID = discord_id
        self.InvitedRoleName = invited_role_name
        self.CurrentlyWatchingRoleName = currently_watching_role_name
        self.AutoCheckSubs = auto_check_subs
        self.SubCheckFrequencyDays = sub_check_frequency_days
        self.TrialRoleName = trial_role_name
        self.AutoCheckTrials = auto_check_trials
        self.TrialLengthMinutes = trial_length_minutes
        self.TrialCheckFrequencyMinutes = trial_check_frequency_minutes
        self.WinnerRoleName = winner_role_name
        self.AutoCheckWinners = auto_check_winners
        self.WinnerWatchTimeThresholdMinutes = winner_watch_time_threshold_minutes
        self.WinnerCheckFrequencyDays = winner_check_frequency_days
        self.WatchlistTemplate = watchlist_template
        self.PlaylistTemplate = playlist_template


class MediaServerRoles(Base):
    __tablename__ = "media_server_roles"
    DiscordServerID = Column(Integer, primary_key=True)
    DiscordRoleName = Column(String)

    @none_as_null
    def __init__(self,
                 discord_id: int,
                 role_name: str):
        self.DiscordServerID = discord_id
        self.DiscordRoleName = role_name


class PlexSettings(Base):
    __tablename__ = "plex_settings"
    EntryID = Column(Integer, autoincrement=True, primary_key=True)
    DiscordServerID = Column(Integer)
    ServerID = Column(Integer)
    ServerName = Column(String(200))
    ServerAltName = Column(String(200))
    ServerURL = Column(String(200))
    ServerToken = Column(String(200))
    TautulliServerID = Column(Integer)

    @none_as_null
    def __init__(self,
                 discord_id: int,
                 server_id: int,
                 server_name: str,
                 server_url: str,
                 server_token: str,
                 server_alt_name: str = null(),
                 tautulli_server_id: int = null()):
        self.DiscordServerID = discord_id
        self.ServerID = server_id
        self.ServerName = server_name
        self.ServerAltName = server_alt_name
        self.ServerURL = server_url
        self.ServerToken = server_token
        self.TautulliServerID = tautulli_server_id


class TautulliSettings(Base):
    __tablename__ = "tautulli_settings"
    EntryID = Column(Integer, autoincrement=True, primary_key=True)
    DiscordServerID = Column(Integer)
    PlexServerNumber = Column(Integer)
    ServerName = Column(String(200))
    ServerURL = Column(String(200))
    ServerAPIKey = Column(String(200))

    @none_as_null
    def __init__(self,
                 discord_id: int,
                 server_name: str,
                 server_url: str,
                 server_api_key: str,
                 plex_server_number: int):
        self.DiscordServerID = discord_id
        self.PlexServerNumber = plex_server_number
        self.ServerName = server_name
        self.ServerURL = server_url
        self.ServerAPIKey = server_api_key


class OmbiSettings(Base):
    __tablename__ = "ombi_settings"
    EntryID = Column(Integer, autoincrement=True, primary_key=True)
    DiscordServerID = Column(Integer)
    ServerName = Column(String(200))
    ServerURL = Column(String(200))
    ServerAPIKey = Column(String(200))

    @none_as_null
    def __init__(self,
                 discord_id: int,
                 server_name: str,
                 server_url: str,
                 server_api_key: str):
        self.DiscordServerID = discord_id
        self.ServerName = server_name
        self.ServerURL = server_url
        self.ServerAPIKey = server_api_key


class JellyfinSettings(Base):
    __tablename__ = "jellyfin_settings"
    EntryID = Column(Integer, autoincrement=True, primary_key=True)
    DiscordServerID = Column(Integer)
    ServerID = Column(Integer)
    ServerName = Column(String(200))
    ServerAltName = Column(String(200))
    ServerURL = Column(String(200))
    ServerAPIKey = Column(String(200))

    @none_as_null
    def __init__(self,
                 discord_id: int,
                 server_id: int,
                 server_name: str,
                 server_url: str,
                 server_api_key: str,
                 server_alt_name: str = null()):
        self.DiscordServerID = discord_id
        self.ServerID = server_id
        self.ServerName = server_name
        self.ServerAltName = server_alt_name
        self.ServerURL = server_url
        self.ServerAPIKey = server_api_key


class EmbySettings(Base):
    __tablename__ = "emby_settings"
    EntryID = Column(Integer, autoincrement=True, primary_key=True)
    DiscordServerID = Column(Integer)
    ServerID = Column(Integer)
    ServerName = Column(String(200))
    ServerAltName = Column(String(200))
    ServerURL = Column(String(200))
    ServerAPIKey = Column(String(200))

    @none_as_null
    def __init__(self,
                 discord_id: int,
                 server_id: int,
                 server_name: str,
                 server_url: str,
                 server_api_key: str,
                 server_alt_name: str = null()):
        self.DiscordServerID = discord_id
        self.ServerID = server_id
        self.ServerName = server_name
        self.ServerAltName = server_alt_name
        self.ServerURL = server_url
        self.ServerAPIKey = server_api_key