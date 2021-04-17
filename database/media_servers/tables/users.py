from database.tools import *

class MediaServerUserTable:
    DiscordID = Column(Integer, primary_key=True)
    MediaServerUsername = Column(String(100))
    MediaServerID = Column(String(200))
    ExpirationStamp = Column(Integer)
    PayMethod = Column(String(100))
    SubType = Column(String(100))

    @none_as_null
    def __init__(self,
                 discord_id: int = null(),
                 media_server_username: str = null(),
                 media_server_id: str = null(),
                 expiration_stamp: int = null(),
                 pay_method: str = null(),
                 user_type: str = null()):
        self.DiscordID = discord_id
        self.MediaServerUsername = media_server_username
        self.MediaServerID = media_server_id
        self.ExpirationStamp = expiration_stamp
        self.PayMethod = pay_method
        self.SubType = user_type


class PlexUser(MediaServerUserTable, Base):
    __tablename__ = "plex"
    Email = Column(String(100))
    WhichPlexServer = Column(Integer)
    WhichTautServer = Column(Integer)

    @none_as_null
    def __init__(self,
                 discord_id: int,
                 plex_username: str,
                 user_type: str,
                 email: str = null(),
                 which_plex_server: int = null(),
                 which_tautulli_server: int = null(),
                 expiration_stamp: int = null(),
                 pay_method: str = null(),
                 ):
        super().__init__(discord_id=discord_id,
                         media_server_username=plex_username,
                         pay_method=pay_method,
                         user_type=user_type,
                         expiration_stamp=expiration_stamp)
        self.Email = email
        self.WhichPlexServer = which_plex_server
        self.WhichTautServer = which_tautulli_server


class EmbyUser(MediaServerUserTable, Base):
    __tablename__ = "emby"

    @none_as_null
    def __init__(self,
                 discord_id: int,
                 emby_username: str,
                 emby_id: str,
                 user_type: str,
                 expiration_stamp: int = null(),
                 pay_method: str = null()):
        super().__init__(discord_id=discord_id,
                         media_server_username=emby_username,
                         media_server_id=emby_id,
                         pay_method=pay_method,
                         user_type=user_type,
                         expiration_stamp=expiration_stamp)


class JellyfinUser(MediaServerUserTable, Base):
    __tablename__ = "jellyfin"

    @none_as_null
    def __init__(self,
                 discord_id: int,
                 jellyfin_username: str,
                 jellyfin_id: str,
                 user_type: str,
                 expiration_stamp: int = null(),
                 pay_method: str = null()):
        super().__init__(discord_id=discord_id,
                         media_server_username=jellyfin_username,
                         media_server_id=jellyfin_id,
                         pay_method=pay_method,
                         user_type=user_type,
                         expiration_stamp=expiration_stamp)
