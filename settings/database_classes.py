import time
from functools import wraps
from typing import Union, List

from sqlalchemy import Column, Integer, Unicode, UnicodeText, String, BigInteger, null, Boolean
from sqlalchemy.ext.declarative import declarative_base

import helper.database as db
from helper.decorators import none_as_null

Base = declarative_base()

class MediaServerSettingsTable(Base):
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

class MediaServerRolesTable(Base):
    DiscordServerID = Column(Integer)
    DiscordRoleName = Column(String)


class PlexSettingsTable(Base):
    ID = Column(Integer, autoincrement=True)
    DiscordServerID = Column(Integer)
    PlexServerName = Column(String(200))
    PlexServerAlternateName = Column(String(200))
    TautulliServerID = Column(Integer)


class TautulliSettingsTable(Base):
    ID = Column(Integer, autoincrement=True)
    DiscordServerID = Column(Integer)
    TautulliServerName = Column(String(200))
    PlexServerID = Column(Integer)


class OmbiSettingsTable(Base):
    ID = Column(Integer, autoincrement=True)
    DiscordServerID = Column(Integer)


class JellyfinSettingsTable(Base):
    ID = Column(Integer, autoincrement=True)
    DiscordServerID = Column(Integer)


class EmbySettingsTable(Base):
    ID = Column(Integer, autoincrement=True)
    DiscordServerID = Column(Integer)


class DiscordAdminsTable(Base):
    DiscordServerID = Column(Integer)
    DiscordAdminID = Column(Integer, nullable=True)
    DiscordAdminRole = Column(Integer, nullable=True)

class CogsEnabledTable(Base):
    DiscordServerID = Column(Integer)
    CogName = Column(String)


class SettingsDatabase(db.SQLAlchemyDatabase):
    def __init__(self,
                 sqlite_file: str,
                 encrypted: bool = False,
                 key_file: str = None):
        super().__init__(sqlite_file=sqlite_file, encrypted=encrypted, key_file=key_file)

    def get_admin_users_and_roles(self, discord_server_id: int):
        return self.session.query(DiscordAdminsTable).filter(DiscordAdminsTable.DiscordServerID == discord_server_id).all()

    def get_plex_servers(self, discord_server_id: int):
        return self.session.query(PlexSettingsTable).filter(PlexSettingsTable.DiscordServerID == discord_server_id).all()

    def get_emby_servers(self, discord_server_id: int):
        return self.session.query(EmbySettingsTable).filter(EmbySettingsTable.DiscordServerID == discord_server_id).all()

    def get_jellyfin_servers(self, discord_server_id: int):
        return self.session.query(JellyfinSettingsTable).filter(JellyfinSettingsTable.DiscordServerID == discord_server_id).all()

    def get_tautulli_server(self, tautulli_server_id: int):
        return self.session.query(TautulliSettingsTable).filter(TautulliSettingsTable.ID == tautulli_server_id)

    def get_ombi_server(self, discord_server_id: int):
        return self.session.query(OmbiSettingsTable).filter(OmbiSettingsTable.DiscordServerID == discord_server_id)
        # Don't need to associate Ombi with Plex/Tautulli, since one Ombi can have multiple Plex/Tautulli pairs
