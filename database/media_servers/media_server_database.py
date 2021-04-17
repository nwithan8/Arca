import time
from typing import Union, List

from database.media_servers.tables.blacklist import BlacklistEntry
from database.media_servers.tables.settings import MediaServerSettings
from database.media_servers.tables.users import EmbyUser, PlexUser, JellyfinUser
from database.tools import *

import helper.database_class as db


class DiscordMediaServerConnectorDatabase(db.SQLAlchemyDatabase):
    def __init__(self,
                 sqlite_file: str,
                 encrypted: bool = False,
                 key_file: str = None,
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

    def get_server_settings(self, media_server_type: str):
        return self.session.query(MediaServerSettings).filter(MediaServerSettings.MediaServerType == media_server_type)

    def get_default_server_number(self, media_server_type: str):
        return self.get_server_settings(media_server_type=media_server_type).DefaultNumber

    def update_default_server_number(self, media_server_type: str, server_number: int):
        settings = self.get_server_settings(media_server_type=media_server_type)
        settings.DefaultNumber = server_number
        self.commit()

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

    def get_user(self, discord_id=None, media_server_username=None, media_server_id=None,
                 first_match_only: bool = False) -> List[Union[PlexUser, JellyfinUser, EmbyUser]]:
        users = []
        for user in self.users:
            if (discord_id and user.DiscordID == discord_id) or (
                    media_server_username and user.MediaServerUsername == media_server_username) or (
                    media_server_id and user.MediaServerID == media_server_id):
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
        return self.session.query(self.table).filter(self.table.SubType == 'Trial').filter(
            self.table.ExpirationStamp <= int(time.time())).all()

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
        self.commit()
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
