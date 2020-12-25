import time
from functools import wraps
from typing import Union, List

from sqlalchemy import Column, Integer, Unicode, UnicodeText, String, BigInteger, null
from sqlalchemy.ext.declarative import declarative_base

import helper.database as db

Base = declarative_base()


def none_as_null(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        """
        Replace None as null()
        """
        func(self, *args, **kwargs)
        for k, v in self.__dict__.items():
            if v is None:
                setattr(self, k, null())
    return wrapper

class BlacklistEntry(Base):
    __tablename__ = "blacklist"
    IDorUsername = Column(String(200), primary_key=True)

    def __init__(self, id_or_username: str):
        self.IDorUsername = id_or_username


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


class DiscordMediaServerConnectorDatabase(db.SQLAlchemyDatabase):
    def __init__(self,
                 sqlite_file: str,
                 encrypted: bool = False,
                 key_file: str = None,
                 use_dropbox: bool = False,
                 media_server_type: str = Union['plex', 'jellyfin', 'emby'],
                 trial_length: int = 0,
                 multi_plex: bool = False):
        self.platform = media_server_type
        self.trial_length = trial_length
        self.multi_plex = multi_plex
        super().__init__(sqlite_file=sqlite_file, encrypted=encrypted, key_file=key_file)



    @property
    def table(self):
        if self.platform == "plex":
            return PlexUser
        elif self.platform == "emby":
            return EmbyUser
        elif self.platform == "jellyfin":
            return JellyfinUser
        return None


    def make_user(self, **kwargs):
        if self.platform == "plex":
            return PlexUser(**kwargs)
        elif self.platform == "emby":
            return EmbyUser(**kwargs)
        elif self.platform == "jellyfin":
            return JellyfinUser(**kwargs)


    @property
    def users(self) -> List[Union[PlexUser, JellyfinUser, EmbyUser]]:
        if not self.table:
            return []
        return self.session.query(self.table).all()


    def get_user(self, discord_id = None, media_server_username = None, media_server_id = None, first_match_only: bool = False) -> List[Union[PlexUser, JellyfinUser, EmbyUser]]:
        users = []
        for user in self.users:
            if (discord_id and user.DiscordID == discord_id) or (media_server_username and user.MediaServerUsername == media_server_username) or (media_server_id and user.MediaServerID == media_server_id):
                users.append(user)
        if first_match_only:
            return [users[0]] if users else []
        return users


    def add_user_to_database(self, user: Union[PlexUser, EmbyUser, JellyfinUser]) -> bool:
        self.session.add(user)
        self.commit()
        return True


    def remove_user_from_database(self, user: Union[PlexUser, EmbyUser, JellyfinUser]):
        if not self.table:
            return False
        self.session.query(self.table).filter(self.table.DiscordID == user.DiscordID).delete()
        self.commit()
        return True


    def edit_user(self, user: Union[PlexUser, EmbyUser, JellyfinUser], **kwargs):
        user_attribute_names = dir(user)
        for k, v in kwargs.items():
            if k in user_attribute_names:
                setattr(__obj=user, __name=k, __value=v)
        self.commit()


    @property
    def winners(self) -> List[Union[PlexUser, EmbyUser, JellyfinUser]]:
        if not self.table:
            return []
        return self.session.query(self.table).filter(self.table.SubType == 'Winner').all()


    @property
    def trials(self) -> List[Union[PlexUser, EmbyUser, JellyfinUser]]:
        if not self.table:
            return []
        return self.session.query(self.table).filter(self.table.SubType == 'Trial').all()


    @property
    def expired_trials(self) -> List[Union[PlexUser, EmbyUser, JellyfinUser]]:
        if not self.table:
            return []
        return self.session.query(self.table).filter(self.table.SubType == 'Trial').filter( self.table.ExpirationStamp <= int(time.time())).all()


    def on_blacklist(self, names_and_ids: List) -> bool:
        for elem in names_and_ids:
            results = self.session.query(BlacklistEntry).filter(BlacklistEntry.IDorUsername == elem).all()
            if results:
                return True
        return False


    def add_to_blacklist(self, name_or_id: Union[str, int]) -> bool:
        if isinstance(name_or_id, int):
            name_or_id = str(name_or_id)
        new_entry = BlacklistEntry(id_or_username=name_or_id)
        self.session.add(new_entry)
        return True


    def remove_from_blacklist(self, name_or_id: Union[str, int]) -> bool:
        if isinstance(name_or_id, int):
            name_or_id = str(name_or_id)
        self.session.query(BlacklistEntry).filter(BlacklistEntry.IDorUsername == name_or_id).delete()
        self.commit()
        return True


    @property
    def blacklist(self) -> List[BlacklistEntry]:
        return self.session.query(BlacklistEntry).all()
