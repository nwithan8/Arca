import time
from functools import wraps
from typing import Union, List

from sqlalchemy import Column, Integer, Unicode, UnicodeText, String, BigInteger, null, Boolean
from sqlalchemy.ext.declarative import declarative_base

import helper.database as db
from helper.decorators import none_as_null

Base = declarative_base()


class MediaServerSettings(Base):
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
    DiscordServerID = Column(Integer)
    DiscordRoleName = Column(String)

    @none_as_null
    def __init__(self,
                 discord_id: int,
                 role_name: str):
        self.DiscordServerID = discord_id
        self.DiscordRoleName = role_name


class PlexSettings(Base):
    EntryID = Column(Integer, autoincrement=True)
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
    EntryID = Column(Integer, autoincrement=True)
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
    EntryID = Column(Integer, autoincrement=True)
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
    EntryID = Column(Integer, autoincrement=True)
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
    EntryID = Column(Integer, autoincrement=True)
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


class DiscordAdmins(Base):
    DiscordServerID = Column(Integer)
    DiscordAdminID = Column(Integer, nullable=True)
    DiscordAdminRole = Column(Integer, nullable=True)

    @none_as_null
    def __init__(self,
                 discord_id: int,
                 admin_id: int = None,
                 admin_role: str = None):
        if not admin_role and not admin_id:
            raise Exception("Must provide either admin role or admin ID when adding an admin to database.")
        self.DiscordServerID = discord_id
        self.DiscordAdminID = admin_id
        self.DiscordAdminRole = admin_role


class CogsEnabled(Base):
    DiscordServerID = Column(Integer)
    CogName = Column(String)

    @none_as_null
    def __init__(self,
                 discord_id: int,
                 cog_name: str):
        self.DiscordServerID = discord_id
        self.CogName = cog_name


class SettingsDatabase(db.SQLAlchemyDatabase):
    def __init__(self,
                 sqlite_file: str,
                 encrypted: bool = False,
                 key_file: str = None):
        super().__init__(sqlite_file=sqlite_file, encrypted=encrypted, key_file=key_file)

    # Cogs
    def get_enabled_cogs(self, discord_server_id: int) -> List[CogsEnabled]:
        return self.session.query(CogsEnabled).filter(CogsEnabled.DiscordServerID == discord_server_id).all()

    def get_enabled_cogs_names(self, discord_server_id: int) -> List[str]:
        all_enabled_cogs = self.get_enabled_cogs(discord_server_id=discord_server_id)
        if not all_enabled_cogs:
            return []
        return [cog.CogName for cog in all_enabled_cogs]

    def is_cog_enabled(self, discord_server_id: int, cog_name: str) -> bool:
        all_enabled_cogs_names = self.get_enabled_cogs_names(discord_server_id=discord_server_id)
        if cog_name in all_enabled_cogs_names:
            return True
        return False

    def enable_cog(self, discord_server_id: int, cog_name: str) -> bool:
        all_enabled_cogs = self.get_enabled_cogs_names(discord_server_id=discord_server_id)
        if cog_name in all_enabled_cogs:
            return True
        new_cog = CogsEnabled(discord_id=discord_server_id,
                              cog_name=cog_name)
        self.session.add(new_cog)
        self.session.commit()
        return True

    def disable_cog(self, discord_server_id: int, cog_name: str) -> bool:
        all_enabled_cogs = self.get_enabled_cogs(discord_server_id=discord_server_id)
        for cog in all_enabled_cogs:
            if cog.CogName == cog_name:
                cog.delete()
        self.session.commit()
        return True

    # Discord
    def get_admin_users_and_roles(self, discord_server_id: int) -> List[DiscordAdmins]:
        return self.session.query(DiscordAdmins).filter(
            DiscordAdmins.DiscordServerID == discord_server_id).all()

    def get_admin_users_ids(self, discord_server_id: int) -> List[int]:
        all_roles_and_ids = self.get_admin_users_and_roles(discord_server_id=discord_server_id)
        ids = []
        for item in all_roles_and_ids:
            if item.DiscordAdminID:
                ids.append(item.DiscordAdminID)
        return ids

    def get_admin_roles_names(self, discord_server_id: int) -> List[str]:
        all_roles_and_ids = self.get_admin_users_and_roles(discord_server_id=discord_server_id)
        roles = []
        for item in all_roles_and_ids:
            if item.DiscordAdminRole:
                roles.append(item.DiscordAdminRole)
        return roles

    def add_admin_user_or_role(self, discord_server_id: int, role: str = None, user_id: int = None) -> bool:
        if not user_id and not role:
            return False
        new_entry = DiscordAdmins(discord_id=discord_server_id,
                                  admin_role=role,
                                  admin_id=user_id)
        self.session.add(new_entry)
        self.session.commit()
        return True

    def remove_admin_user_or_role(self, discord_server_id: int, role: str = None, user_id: int = None) -> bool:
        if not user_id and not role:
            return False
        all_roles_and_ids = self.get_admin_users_and_roles(discord_server_id=discord_server_id)
        for entry in all_roles_and_ids:
            if user_id and entry.DiscordAdminID == user_id:
                entry.delete()
            elif role and entry.DiscordAdminRole == role:
                entry.delete()
        self.session.commit()
        return True

    # Plex
    def get_plex_servers(self, discord_server_id: int) -> List[PlexSettings]:
        return self.session.query(PlexSettings).filter(
            PlexSettings.DiscordServerID == discord_server_id).all()

    def get_plex_server(self, discord_server_id: int, server_number: int = None, server_name: str = None) -> \
            Union[PlexSettings, None]:
        all_servers = self.get_plex_servers(discord_server_id=discord_server_id)
        if not all_servers:
            return None
        if not server_name and not server_number:  # note this workaround
            return all_servers[0]
        for server in all_servers:
            if server_name and (server.ServerName == server_name or server.ServerAltName == server_name):
                return server
            if server_number and server.ServerID == server_number:
                return server
        return None

    def add_plex_server(self, discord_server_id: int, name: str, url: str, token: str, alt_name: str = None):
        new_server_id = self._get_new_media_server_number(current_servers=self.get_plex_servers(discord_server_id=discord_server_id))
        new_server = PlexSettings(discord_id=discord_server_id,
                                  server_id=new_server_id,
                                  server_name=name,
                                  server_alt_name=alt_name,
                                  server_url=url,
                                  server_token=token)
        self.session.add(new_server)
        self.session.commit()

    def remove_plex_server(self, discord_server_id: int, server_number: int = None, server_name: str = None) -> bool:
        if not server_name and not server_number:
            return False

        all_servers = self.get_plex_servers(discord_server_id=discord_server_id)
        if not all_servers:
            return False

        server_to_delete = None
        for server in all_servers:
            if server_name and (server.ServerName == server_name or server.ServerAltName == server_name):
                server_to_delete = server
            if server_number and server.ServerID == server_number:
                server_to_delete = server
        if server_to_delete:
            server_to_delete.delete()
            self.session.commit()
            return True
        return False

    # Emby
    def get_emby_servers(self, discord_server_id: int) -> List[EmbySettings]:
        return self.session.query(EmbySettings).filter(
            EmbySettings.DiscordServerID == discord_server_id).all()

    def get_emby_server(self, discord_server_id: int, server_number: int = None, server_name: str = None) -> \
            Union[EmbySettings, None]:
        all_servers = self.get_emby_servers(discord_server_id=discord_server_id)
        if not all_servers:
            return None
        if not server_name and not server_number:  # note this workaround
            return all_servers[0]
        for server in all_servers:
            if server_name and (server.ServerName == server_name or server.ServerAltName == server_name):
                return server
            if server_number and server.ServerID == server_number:
                return server
        return None

    def add_emby_server(self, discord_server_id: int, name: str, url: str, api_key: str, alt_name: str = None):
        new_server_id = self._get_new_media_server_number(current_servers=self.get_emby_servers(discord_server_id=discord_server_id))
        new_server = EmbySettings(discord_id=discord_server_id,
                                  server_id=new_server_id,
                                  server_name=name,
                                  server_alt_name=alt_name,
                                  server_url=url,
                                  server_api_key=api_key)
        self.session.add(new_server)
        self.session.commit()

    def remove_emby_server(self, discord_server_id: int, server_number: int = None, server_name: str = None) -> bool:
        if not server_name and not server_number:
            return False

        all_servers = self.get_plex_servers(discord_server_id=discord_server_id)
        if not all_servers:
            return False

        server_to_delete = None
        for server in all_servers:
            if server_name and (server.ServerName == server_name or server.ServerAltName == server_name):
                server_to_delete = server
            if server_number and server.ServerID == server_number:
                server_to_delete = server
        if server_to_delete:
            server_to_delete.delete()
            self.session.commit()
            return True
        return False

    # Jellyfin
    def get_jellyfin_servers(self, discord_server_id: int) -> List[JellyfinSettings]:
        return self.session.query(JellyfinSettings).filter(
            JellyfinSettings.DiscordServerID == discord_server_id).all()

    def get_jellyfin_server(self, discord_server_id: int, server_number: int = None, server_name: str = None) -> \
            Union[JellyfinSettings, None]:
        all_servers = self.get_emby_servers(discord_server_id=discord_server_id)
        if not all_servers:
            return None
        if not server_name and not server_number:  # note this workaround
            return all_servers[0]
        for server in all_servers:
            if server_name and (server.ServerName == server_name or server.ServerAltName == server_name):
                return server
            if server_number and server.ServerID == server_number:
                return server
        return None

    def add_jellyfin_server(self, discord_server_id: int, name: str, url: str, api_key: str, alt_name: str = None):
        new_server_id = self._get_new_media_server_number(current_servers=self.get_jellyfin_servers(discord_server_id=discord_server_id))
        new_server = JellyfinSettings(discord_id=discord_server_id,
                                      server_id=new_server_id,
                                      server_name=name,
                                      server_alt_name=alt_name,
                                      server_url=url,
                                      server_api_key=api_key)
        self.session.add(new_server)
        self.session.commit()

    def remove_jellyfin_server(self, discord_server_id: int, server_number: int = None,
                               server_name: str = None) -> bool:
        if not server_name and not server_number:
            return False

        all_servers = self.get_plex_servers(discord_server_id=discord_server_id)
        if not all_servers:
            return False

        server_to_delete = None
        for server in all_servers:
            if server_name and (server.ServerName == server_name or server.ServerAltName == server_name):
                server_to_delete = server
            if server_number and server.ServerID == server_number:
                server_to_delete = server
        if server_to_delete:
            server_to_delete.delete()
            self.session.commit()
            return True
        return False

    # Tautulli
    def get_tautulli_servers(self, discord_server_id: int) -> List[TautulliSettings]:
        return self.session.query(TautulliSettings).filter(TautulliSettings.DiscordServerID == discord_server_id)

    def get_tautulli_server(self, tautulli_server_entry_id: int) -> TautulliSettings:
        return self.session.query(TautulliSettings).filter(TautulliSettings.EntryID == tautulli_server_entry_id)

    def add_tautulli_server(self, discord_server_id: int, name: str, url: str, api_key: str, plex_server_number: int):
        # sanity check to see if corresponding Plex server exists first
        corresponding_plex_server = self.session.query(PlexSettings).filter(
            PlexSettings.ServerID == plex_server_number).one()
        if not corresponding_plex_server:
            return False

        # make and save new Tautulli server
        new_server = TautulliSettings(discord_id=discord_server_id,
                                      plex_server_number=plex_server_number,
                                      server_name=name,
                                      server_url=url,
                                      server_api_key=api_key)
        self.session.add(new_server)
        self.session.commit()

        # get new Tautulli server entry
        new_server = self.session.query(TautulliSettings).filter(
            TautulliSettings.PlexServerNumber == plex_server_number).one()

        # save Tautulli entry ID to the corresponding Plex server
        corresponding_plex_server.TautulliServerID = new_server.EntryID
        self.session.commit()

    def remove_tautulli_server(self, discord_server_id: int, tautulli_server_entry_id: int = None,
                               plex_server_number: int = None) -> bool:
        if not tautulli_server_entry_id and not plex_server_number:
            return False

        all_servers = self.get_tautulli_servers(discord_server_id=discord_server_id)
        if not all_servers:
            return False

        server_to_delete = None
        for server in all_servers:
            if tautulli_server_entry_id and server.EntryID == tautulli_server_entry_id:
                server_to_delete = server
            if plex_server_number and server.PlexServerNumber == plex_server_number:
                server_to_delete = server
        if server_to_delete:
            plex_server_number = server_to_delete.PlexServerNumber
            server_to_delete.delete()
            self.session.commit()

            # get the corresponding Plex server and remove the Tautulli link
            plex_server = self.get_plex_server(discord_server_id=discord_server_id, server_number=plex_server_number)
            if plex_server:
                plex_server.TautulliServerID = null()
                self.session.commit()
        return True

    # Ombi
    def get_ombi_server(self, discord_server_id: int) -> OmbiSettings:
        return self.session.query(OmbiSettings).filter(OmbiSettings.DiscordServerID == discord_server_id).one()
        # Don't need to associate Ombi with Plex/Tautulli, since one Ombi can have multiple Plex/Tautulli pairs
        # Only one Ombi per Discord Server

    def add_ombi_server(self, discord_server_id: int, name: str, url: str, api_key: str) -> bool:
        current_server_exists = self.session.query(OmbiSettings).filter(OmbiSettings.DiscordServerID == discord_server_id).all()
        if current_server_exists:
            return False  # can't have more than one Ombi per Discord server

        new_server = OmbiSettings(discord_server_id=discord_server_id,
                                  server_name=name,
                                  server_url=url,
                                  server_api_key=api_key)
        self.session.add(new_server)
        self.session.commit()
        return True

    def remove_ombi_server(self, discord_server_id: int) -> bool:
        current_servers = self.get_ombi_server(discord_server_id=discord_server_id).all()
        if not current_servers:
            return False
        for server in current_servers:
            server.delete()
        self.session.commit()
        return True

    # Helpers
    def _get_new_media_server_number(self, current_servers: List = None) -> int:
        new_server_id = 1
        if current_servers:
            server_numbers = [server.ServerID for server in current_servers]
            while True:
                if new_server_id not in server_numbers:
                    break
                new_server_id += 1
        return new_server_id
