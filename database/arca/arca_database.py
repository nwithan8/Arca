from typing import Union, List

from database.arca.tables.admins import DiscordAdmins
from database.arca.tables.cogs import CogsEnabled
from database.arca.tables.settings import BotSettings
from database.media_servers.tables.settings import EmbySettings, PlexSettings, JellyfinSettings, TautulliSettings, \
    OmbiSettings
from database.tools import *

import helper.database_class as db
from helper.decorators import false_if_error
from settings.global_settings import DEFAULT_PREFIX


class ArcaSettingsDatabase(db.SQLAlchemyDatabase):
    def __init__(self,
                 sqlite_file: str,
                 encrypted: bool = False,
                 key_file: str = None):
        super().__init__(sqlite_file=sqlite_file, encrypted=encrypted, key_file=key_file)
        BotSettings.__table__.create(bind=self.engine, checkfirst=True)
        CogsEnabled.__table__.create(bind=self.engine, checkfirst=True)
        DiscordAdmins.__table__.create(bind=self.engine, checkfirst=True)


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

    @false_if_error
    def enable_cog(self, discord_server_id: int, cog_name: str) -> bool:
        all_enabled_cogs = self.get_enabled_cogs_names(discord_server_id=discord_server_id)
        if cog_name in all_enabled_cogs:
            return True
        new_cog = CogsEnabled(discord_id=discord_server_id,
                              cog_name=cog_name)
        self.session.add(new_cog)
        self.session.commit()
        return True

    @false_if_error
    def disable_cog(self, discord_server_id: int, cog_name: str) -> bool:
        all_enabled_cogs = self.get_enabled_cogs(discord_server_id=discord_server_id)
        for cog in all_enabled_cogs:
            if cog.CogName == cog_name:
                self.session.delete(cog)
        self.session.commit()
        return True

    # Bot settings
    def get_prefix(self, discord_server_id: int) -> str:
        result = self.session.query(BotSettings).filter(BotSettings.DiscordServerID == discord_server_id).first()
        if not result or not result.Prefix:
            return DEFAULT_PREFIX
        return result.Prefix

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
