import time
from typing import Union, List

import helper.database as db
from media_server.classes import PlexUser, JellyfinUser, EmbyUser, DiscordUser

class DiscordMediaServerConnectorDatabase(db.Database):
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
        super().__init__(sqlite_file=sqlite_file, encrypted=encrypted, key_file=key_file, use_dropbox=use_dropbox)


    @property
    def _username_field(self):
        if self.platform == "plex":
            return "PlexUsername"
        elif self.platform == "emby":
            return "EmbyUsername"
        elif self.platform == "jellyfin":
            return "JellyfinUsername"
        return ""


    @property
    def _id_field(self):
        if self.platform == "plex":
            return "PlexUsername"
        elif self.platform == "emby":
            return "EmbyID"
        elif self.platform == "jellyfin":
            return "JellyfinID"
        return ""


    def on_blacklist(self, names_and_ids: List) -> bool:
        for elem in names_and_ids:
            query = db.SelectQuery(database_connection=self,
                                   column_names=["*"],
                                   from_table="blacklist",
                                   where=[db.ColumnValuePair(column_name="IDorUsername",
                                                             value=elem)
                                          ])
            if query.execute():
                return True
        return False


    def add_to_blacklist(self, name_or_id: Union[str, int]) -> bool:
        query = db.InsertQuery(database_connection=self,
                               column_value_pairs=[db.ColumnValuePair(column_name="IDorUsername",
                                                                      value=name_or_id)
                                                   ],
                               into_table="blacklist")
        return query.execute()


    def remove_from_blacklist(self, name_or_id: Union[str, int]) -> bool:
        query = db.DeleteQuery(database_connection=self,
                               from_table="blacklist",
                               where=[db.ColumnValuePair(column_name="IDorUsername",
                                                         value=name_or_id)
                                      ])
        return query.execute()


    def get_all_blacklist(self):
        """
        Returns all blacklist entries
        """
        query = db.SelectQuery(database_connection=self,
                               column_names=["*"],
                               from_table="blacklist")
        return query.execute(fetch_all=True)


    def add_user_to_db(self,
                       discord_id: int,
                       username,
                       note: str,
                       uid=None,
                       serverNumber=None):
        value_pairs = [db.ColumnValuePair(column_name="DiscordID",
                                          value=discord_id),
                       db.ColumnValuePair(column_name="SubType",
                                          value=note)]
        timestamp = None
        if note == 't':
            timestamp = int(time.time()) + self.trial_length
            value_pairs.append(db.ColumnValuePair(column_name="ExpirationStamp",
                                                  value=timestamp))
        server_specific_values = [db.ColumnValuePair(column_name=self._username_field, value=username)]
        if self.platform == "plex" and serverNumber:
            server_specific_values.append(db.ColumnValuePair(column_name="WhichPlexServer", value=serverNumber))
        if self.platform != "plex":
            server_specific_values.append(db.ColumnValuePair(column_name=self._id_field, value=uid))
        value_pairs.extend(server_specific_values)
        query = db.InsertQuery(database_connection=self,
                               into_table=self.platform,
                               column_value_pairs=value_pairs)
        run_result = query.execute()
        if note != 't':
            return run_result
        # if trial, update their timestamp
        if self.platform == 'plex':
            username_column = "PlexUsername"
            username_value = username
        else:
            username_column = self._id_field
            username_value = uid
        update_query = db.UpdateQuery(database_connection=self,
                                      table_name=self.platform,
                                      column_value_pairs=[db.ColumnValuePair(column_name="ExpirationStamp",
                                                                             value=timestamp)],
                                      where=[db.ColumnValuePair(column_name=username_column,
                                                                value=username_value)])
        return update_query.execute()


    def remove_user_from_db(self, user_id):
        query = db.DeleteQuery(database_connection=self,
                               from_table=self.platform,
                               where=[db.ColumnValuePair(column_name="DiscordID",
                                                         value=user_id)])
        return query.execute()


    def find_user_in_db(self, value, discord: bool = True):
        """
        Get DiscordID ('Discord')/PlexUsername ('Plex') (PlexOrDiscord) of PlexUsername/DiscordID (data)
        """
        if discord:
            where = [db.ColumnValuePair(column_name="DiscordID", value=value)]
            column_names = [self._id_field, "SubType"]
            if self.platform == "plex" and self.multi_plex:
                column_names.append("WhichPlexServer")
        else: # ServerOrDiscord == "Emby"/"Plex"/"Jellyfin"
            column_names = ["DiscordID"]
            where = [db.ColumnValuePair(column_name=self._id_field, value=value)]
        query = db.SelectQuery(database_connection=self,
                               column_names=column_names,
                               from_table=self.platform,
                               where=where)
        results = query.execute()
        if not results:
            return None
        if discord:
            return DiscordUser(id=int(results[0]))
        else:
            if self.platform == "plex":
                return PlexUser(username=results[0],
                                user_type=results[1],
                                server_number=(int(results[2]) if self.multi_plex else None))
            elif self.platform == "emby":
                return EmbyUser(id=results[0],
                                user_type=results[1])
            elif self.platform == "jellyfin":
                return JellyfinUser(id=results[0],
                                    user_type=results[1])


    def find_username_in_db(self, value, discord: bool = True):
        """
        Returns {Jellyfin/Emby}Username/DiscordID, Note
        """
        if discord:
            column_names = [self._username_field]
            where = [db.ColumnValuePair(column_name="DiscordID", value=value)]
        else: # ServerOrDiscord == "Emby"/"Plex"/"Jellyfin"
            column_names = ["DiscordID"]
            where = [db.ColumnValuePair(column_name=self._username_field, value=value)]
        query = db.SelectQuery(database_connection=self,
                               column_names=column_names,
                               from_table=self.platform,
                               where=where)
        results = query.execute()
        if not results:
            return None
        return results[0]


    def get_all_data_for_server(self):
        """
        Returns all entries for a specific server type (i.e. Emby)
        """
        query = db.SelectQuery(database_connection=self,
                               column_names=['*'],
                               from_table=self.platform)
        results = query.execute(fetch_all=True)
        if not results:
            return []
        return results


    def get_winners(self):
        """
        Get all user ids with 'w' note
        """
        query = db.SelectQuery(database_connection=self,
                               column_names=[self._id_field],
                               from_table=self.platform,
                               where=[db.ColumnValuePair(column_name="SubType", value="w")])
        results = query.execute(fetch_all=True)
        if not results:
            return []
        return results


    def get_trials_discord_id(self):
        """
        Get Discord IDs of all users with an active trial
        :return:
        """
        query = db.SelectQuery(database_connection=self,
                               column_names=["DiscordID"],
                               from_table=self.platform,
                               where=[db.ColumnValuePair(column_name="ExpirationStamp", value=str(int(time.time())), comparison="<="),
                                      db.ColumnValuePair(column_name="SubType", value="t")])
        results = query.execute(fetch_all=True)
        if not results:
            return []
        return results
