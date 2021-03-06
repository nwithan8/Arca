import sqlite3
import time
import helper.dropbox_handler as dbx
import helper.encryption as encryption


def unlock(database, key_file):
    key = encryption.getRawKey(key_file)
    if key:
        database.execute(f'pragma key="{key}"')
        return True
    print("Couldn't get the key to unlock the database.")
    return False


class DB:
    def __init__(self, SQLITE_FILE: str, SERVER_TYPE=None, TRIAL_LENGTH=None, MULTI_PLEX=None,
                 USE_DROPBOX: bool = False,
                 ENCRYPTED: bool = False, KEY_FILE: str = None):
        self.PLATFORM = SERVER_TYPE
        self.SQLITE_FILE = SQLITE_FILE
        self.TRIAL_LENGTH = TRIAL_LENGTH
        self.MULTI_PLEX = MULTI_PLEX
        self.USE_DROPBOX = USE_DROPBOX
        self.ENCRYPTED = ENCRYPTED
        self.KEY_FILE = KEY_FILE
        if self.ENCRYPTED and not self.KEY_FILE:
            raise Exception("Missing KEY_FILE to unlock encrypted database.")

    def crypt_check(self, file):
        if self.ENCRYPTED:
            from pysqlcipher3 import dbapi2 as sqlcipher
            db = sqlcipher.connect(file)
            if unlock(db, self.KEY_FILE):
                return db
            return None
        return sqlite3.connect(file)

    def download(self, file):
        if self.USE_DROPBOX and file:
            return dbx.download_file(file)
        return False

    def upload(self, file):
        if self.USE_DROPBOX and file:
            return dbx.upload_file(file)
        return False

    def backup(self, file, rename=False):
        if self.USE_DROPBOX and file:
            return dbx.upload_file(filePath=file, rename=rename)
        return False

    def describe_table(self, file, table):
        self.download(file)
        conn = self.crypt_check(file)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info([{}])".format(str(table)))
        result = cur.fetchall()
        cur.close()
        conn.close()
        self.upload(file)
        if result:
            return result
        return None

    def check_blacklist(self, name_or_id=None):
        if not name_or_id:
            return None
        else:
            self.download(self.SQLITE_FILE)
            conn = self.crypt_check(self.SQLITE_FILE)
            cur = conn.cursor()
            query = "SELECT * FROM blacklist WHERE IDorUsername = '{}'".format(str(name_or_id))
            cur.execute(query)
            result = cur.fetchone()
            cur.close()
            conn.close()
            self.upload(self.SQLITE_FILE)
            if result:
                return True
            return False

    def add_to_blacklist(self, name_or_id=None):
        if not name_or_id:
            return None
        else:
            self.download(self.SQLITE_FILE)
            result = False
            conn = self.crypt_check(self.SQLITE_FILE)
            cur = conn.cursor()
            query = "INSERT INTO blacklist (IDorUsername) VALUES ('{}')".format(str(name_or_id))
            cur.execute(query)
            if int(cur.rowcount) > 0:
                result = True
            conn.commit()
            cur.close()
            conn.close()
            self.upload(self.SQLITE_FILE)
            return result

    def remove_from_blacklist(self, name_or_id=None):
        if not name_or_id:
            return None
        else:
            self.download(self.SQLITE_FILE)
            conn = self.crypt_check(self.SQLITE_FILE)
            cur = conn.cursor()
            query = "DELETE FROM blacklist WHERE IDorUsername = '{}'".format(str(name_or_id))
            cur.execute(query)
            conn.commit()
            cur.close()
            conn.close()
            self.upload(self.SQLITE_FILE)

    def get_all_blacklist(self):
        """
        Returns all blacklist entries
        """
        self.download(self.SQLITE_FILE)
        conn = self.crypt_check(self.SQLITE_FILE)
        cur = conn.cursor()
        query = "SELECT * FROM blacklist"
        cur.execute(query)
        result = cur.fetchall()
        cur.close()
        conn.close()
        self.upload(self.SQLITE_FILE)
        if result:
            return result
        return None

    def add_user_to_db(self, discordId, username, note, uid=None, serverNumber=None):
        self.download(self.SQLITE_FILE)
        result = False
        conn = self.crypt_check(self.SQLITE_FILE)
        cur = conn.cursor()
        if note == 't':
            timestamp = int(time.time()) + self.TRIAL_LENGTH
            if self.PLATFORM == 'plex':
                # Trial for Plex
                query = "INSERT OR IGNORE INTO plex (DiscordID, PlexUsername, ExpirationStamp{serverNumOpt}, " \
                        "SubType) VALUES ('{discordId}', '{plexUsername}', '{expirationStamp}'{serverNum}, '{note}')' " \
                        "".format(
                    serverNumOpt=(", WhichPlexServer" if serverNumber is not None else ""),
                    discordId=str(discordId),
                    plexUsername=username,
                    expirationStamp=str(timestamp),
                    serverNum=((",'" + serverNumber + "'") if serverNumber else ""),
                    note=str(note))
                cur.execute(str(query))
                query = "UPDATE plex SET ExpirationStamp = '{time} WHERE PlexUsername = '{username}'".format(
                    time=str(timestamp),
                    username=username)
            else:
                # Trial for Jellyfin/Emby
                query = "INSERT OR IGNORE INTO {platform} (DiscordID, {platformCap}Username, {platformCap}ID, " \
                        "ExpirationStamp, SubType) VALUES ('{discordId}', '{username}', '{uid}', '{time}', '{note}') ".format(
                    platform=self.PLATFORM,
                    platformCap=self.PLATFORM.capitalize(),
                    discordId=str(discordId),
                    username=username,
                    uid=uid,
                    time=timestamp,
                    note=note)
                cur.execute(str(query))
                query = "UPDATE {platform} SET ExpirationStamp = '{time}' WHERE {platformCap}ID = '{uid}'".format(
                    platform=self.PLATFORM,
                    platformCap=self.PLATFORM.capitalize(),
                    time=str(timestamp),
                    uid=uid)
            cur.execute(str(query))
            # Awaiting SQLite 3.24 support/adoption to use cleaner UPSERT function
        else:
            if self.PLATFORM == 'plex':
                # Regular for Plex
                query = "INSERT OR IGNORE INTO plex (DiscordID, PlexUsername{serverNumOpt}, SubType) VALUES ('" \
                        "{discordId}','{plexUsername}'{serverNum}, '{note}')".format(
                    serverNumOpt=(", WhichPlexServer" if serverNumber is not None else ""),
                    discordId=str(discordId),
                    plexUsername=username,
                    serverNum=((",'" + str(serverNumber) + "'") if serverNumber is not None else ""),
                    note=note)
            else:
                # Regular for Jellyfin/Emby
                query = "INSERT OR IGNORE INTO {platform} (DiscordID, {platformCap}Username, {platformCap}ID, SubType) VALUES ('" \
                        "{discordId}', '{username}', '{uid}', '{note}')".format(
                    platform=self.PLATFORM,
                    platformCap=self.PLATFORM.capitalize(),
                    discordId=discordId,
                    username=username,
                    uid=uid,
                    note=note)
            cur.execute(str(query))
        if int(cur.rowcount) > 0:
            result = True
        conn.commit()
        cur.close()
        conn.close()
        self.upload(self.SQLITE_FILE)
        return result

    def remove_user_from_db(self, id):
        self.download(self.SQLITE_FILE)
        conn = self.crypt_check(self.SQLITE_FILE)
        cur = conn.cursor()
        cur.execute(str(
            "DELETE FROM {platform} WHERE DiscordID = '{idNumber}'".format(platform=self.PLATFORM, idNumber=str(id))))
        conn.commit()
        cur.close()
        conn.close()
        self.upload(self.SQLITE_FILE)

    def find_user_in_db(self, ServerOrDiscord, data):
        """
        Get DiscordID ('Discord')/PlexUsername ('Plex') (PlexOrDiscord) of PlexUsername/DiscordID (data)
        """
        self.download(self.SQLITE_FILE)
        conn = self.crypt_check(self.SQLITE_FILE)
        cur = conn.cursor()
        if self.PLATFORM == 'plex':
            # Find Plex User -> Username, SubType, WhichPlexServer
            query = "SELECT {getWhat} FROM plex WHERE {whereWhat} = '{data}'".format(
                getWhat=("PlexUsername, SubType" + (
                    ", WhichPlexServer" if self.MULTI_PLEX else "") if ServerOrDiscord is not 'Discord' else "DiscordID"),
                whereWhat=("DiscordID" if ServerOrDiscord is not 'Discord' else "PlexUsername"),
                data=str(data))
        else:
            # Find Jellyfin/Emby User -> ID
            query = "SELECT {getWhat} FROM {platform} WHERE {whereWhat} = '{data}'".format(
                getWhat=(
                    "{}ID".format(self.PLATFORM.capitalize()) if ServerOrDiscord is not 'Discord' else "DiscordID"),
                platform=self.PLATFORM,
                whereWhat=(
                    "DiscordID" if ServerOrDiscord is not 'Discord' else "{}ID".format(self.PLATFORM.capitalize())),
                data=str(data))
        cur.execute(str(query))
        results = cur.fetchone()
        cur.close()
        conn.close()
        self.upload(self.SQLITE_FILE)
        if results:
            return results if self.PLATFORM == 'plex' else results[0]
            # returns [name, note], [name, note, number] or [id]
        else:
            if self.PLATFORM is not 'plex':
                return None
            if ServerOrDiscord == "Plex":
                if self.MULTI_PLEX:
                    return None, None, None
                return None, None
            return None

    def find_username_in_db(self, ServerOrDiscord, data):
        """
        Returns {Jellyfin/Emby}Username/DiscordID, Note
        """
        self.download(self.SQLITE_FILE)
        conn = self.crypt_check(self.SQLITE_FILE)
        cur = conn.cursor()
        query = "SELECT {what}, Note FROM {platform} WHERE {whereWhat} = '{filter}'".format(
            what=("{}Username".format(self.PLATFORM.capitalize()) if ServerOrDiscord is not 'Discord' else "DiscordID"),
            platform=self.PLATFORM,
            where=(
                "DiscordID" if ServerOrDiscord is not 'Discord' else "{}Username".format(self.PLATFORM.capitalize())),
            filter=str(data))
        cur.execute(str(query))
        result = cur.fetchone()
        cur.close()
        conn.close()
        self.upload(self.SQLITE_FILE)
        if result:
            return result[0], result[1]
        return None, None

    def find_entry_in_db(self, fieldType, data):
        """
        Returns whole entry
        """
        self.download(self.SQLITE_FILE)
        conn = self.crypt_check(self.SQLITE_FILE)
        cur = conn.cursor()
        query = "SELECT * FROM {platform} WHERE {where} = '{filter}'".format(platform=self.PLATFORM, where=fieldType,
                                                                             filter=str(data))
        cur.execute(query)
        result = cur.fetchone()
        cur.close()
        conn.close()
        self.upload(self.SQLITE_FILE)
        if result:
            return result
        return None

    def get_all_entries_in_db(self):
        """
        Returns all database entries
        """
        self.download(self.SQLITE_FILE)
        conn = self.crypt_check(self.SQLITE_FILE)
        cur = conn.cursor()
        query = "SELECT * FROM {platform}".format(platform=self.PLATFORM)
        cur.execute(query)
        result = cur.fetchall()
        cur.close()
        conn.close()
        self.upload(self.SQLITE_FILE)
        if result:
            return result
        return None

    def get_winners(self):
        """
        Get all users with 'w' note
        """
        self.download(self.SQLITE_FILE)
        conn = self.crypt_check(self.SQLITE_FILE)
        cur = conn.cursor()
        cur.execute("SELECT {what} FROM {platform} WHERE SubType = 'w'".format(
            what='PlexUsername' if self.PLATFORM == 'plex' else "{}ID".format(self.PLATFORM.capitalize()),
            platform=self.PLATFORM))
        results = cur.fetchall()
        cur.close()
        conn.close()
        self.upload(self.SQLITE_FILE)
        return results

    def get_trials(self):
        self.download(self.SQLITE_FILE)
        conn = self.crypt_check(self.SQLITE_FILE)
        cur = conn.cursor()
        query = "SELECT DiscordID FROM {platform} WHERE ExpirationStamp<={stamp} AND SubType = 't'".format(
            platform=self.PLATFORM, stamp=str(int(time.time())))
        cur.execute(str(query))
        results = cur.fetchall()
        cur.close()
        conn.close()
        self.upload(self.SQLITE_FILE)
        return results

    def custom_query(self, query):
        self.download(self.SQLITE_FILE)
        conn = self.crypt_check(self.SQLITE_FILE)
        cur = conn.cursor()
        cur.execute(str(query))
        results = cur.fetchall()
        conn.commit()
        cur.close()
        conn.close()
        self.upload(self.SQLITE_FILE)
        return results
