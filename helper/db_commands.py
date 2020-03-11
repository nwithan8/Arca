import sqlite3
import time

import helper.dropbox_handler as dbx


class DB:
    def __init__(self, SERVER_TYPE, SQLITE_FILE, TRIAL_LENGTH, MULTI_PLEX=None, BLACKLIST_FILE=None, USE_DROPBOX=False):
        self.PLATFORM = SERVER_TYPE
        self.SQLITE_FILE = SQLITE_FILE
        self.BLACKLIST_FILE = BLACKLIST_FILE
        self.TRIAL_LENGTH = TRIAL_LENGTH
        self.MULTI_PLEX = MULTI_PLEX
        self.USE_DROPBOX = USE_DROPBOX

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
        conn = sqlite3.connect(file)
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
            self.download(self.BLACKLIST_FILE)
            conn = sqlite3.connect(self.BLACKLIST_FILE)
            cur = conn.cursor()
            query = "SELECT * FROM blacklist WHERE id_or_username = '{}'".format(str(name_or_id))
            cur.execute(query)
            result = cur.fetchone()
            cur.close()
            conn.close()
            self.upload(self.BLACKLIST_FILE)
            if result:
                return True
            return False

    def add_to_blacklist(self, name_or_id=None):
        if not name_or_id:
            return None
        else:
            self.download(self.BLACKLIST_FILE)
            result = False
            conn = sqlite3.connect(self.BLACKLIST_FILE)
            cur = conn.cursor()
            query = "INSERT INTO blacklist (id_or_username) VALUES ('{}')".format(str(name_or_id))
            cur.execute(query)
            if int(cur.rowcount) > 0:
                result = True
            conn.commit()
            cur.close()
            conn.close()
            self.upload(self.BLACKLIST_FILE)
            return result

    def remove_from_blacklist(self, name_or_id=None):
        if not name_or_id:
            return None
        else:
            self.download(self.BLACKLIST_FILE)
            conn = sqlite3.connect(self.BLACKLIST_FILE)
            cur = conn.cursor()
            query = "DELETE FROM blacklist WHERE id_or_username = '{}'".format(str(name_or_id))
            cur.execute(query)
            conn.commit()
            cur.close()
            conn.close()
            self.upload(self.BLACKLIST_FILE)

    def get_all_blacklist(self):
        """
        Returns all blacklist entries
        """
        self.download(self.BLACKLIST_FILE)
        conn = sqlite3.connect(self.BLACKLIST_FILE)
        cur = conn.cursor()
        query = "SELECT * FROM blacklist"
        cur.execute(query)
        result = cur.fetchall()
        cur.close()
        conn.close()
        self.upload(self.BLACKLIST_FILE)
        if result:
            return result
        return None

    def add_user_to_db(self, discordId, username, note, uid=None, serverNumber=None):
        self.download(self.SQLITE_FILE)
        result = False
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        if note == 't':
            timestamp = int(time.time()) + self.TRIAL_LENGTH
            if self.PLATFORM == 'Plex':
                # Trial for Plex
                query = "INSERT OR IGNORE INTO users (DiscordID, PlexUsername, ExpirationStamp{serverNumOpt}, " \
                        "Note) VALUES ('{discordId}', '{plexUsername}', '{expirationStamp}'{serverNum}, '{note}')' " \
                        "".format(
                    serverNumOpt=(", ServerNum" if serverNumber is not None else ""),
                    discordId=str(discordId),
                    plexUsername=username,
                    expirationStamp=str(timestamp),
                    serverNum=((",'" + serverNumber + "'") if serverNumber else ""),
                    note=str(note))
                cur.execute(str(query))
                query = "UPDATE users SET ExpirationStamp = '{time} WHERE PlexUsername = '{username}'".format(
                    time=str(timestamp),
                    username=username)
            else:
                # Trial for Jellyfin/Emby
                query = "INSERT OR IGNORE INTO users (DiscordID, {platform}Username, {platform}ID, ExpirationStamp, " \
                        "Note) VALUES ('{discordId}', '{username}', '{uid}', '{time}', '{note}') ".format(
                    platform=self.PLATFORM,
                    discordId=str(discordId),
                    username=username,
                    uid=uid,
                    time=timestamp,
                    note=note)
                cur.execute(str(query))
                query = "UPDATE users SET ExpirationStamp = '{time}' WHERE {platform}ID = '{uid}'".format(
                    platform=self.PLATFORM,
                    time=str(timestamp),
                    uid=uid)
            cur.execute(str(query))
            # Awaiting SQLite 3.24 support/adoption to use cleaner UPSERT function
        else:
            if self.PLATFORM == 'Plex':
                # Regular for Plex
                query = "INSERT OR IGNORE INTO users (DiscordID, PlexUsername{serverNumOpt}, Note) VALUES ('" \
                        "{discordId}','{plexUsername}'{serverNum}, '{note}')".format(
                    serverNumOpt=(", ServerNum" if serverNumber is not None else ""),
                    discordId=str(discordId),
                    plexUsername=username,
                    serverNum=((",'" + str(serverNumber) + "'") if serverNumber is not None else ""),
                    note=note)
            else:
                # Regular for Jellyfin/Emby
                query = "INSERT OR IGNORE INTO users (DiscordID, {platform}Username, {platform}ID, Note) VALUES ('" \
                        "{discordId}', '{username}', '{uid}', '{note}')".format(
                    platform=self.PLATFORM,
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
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        cur.execute(str("DELETE FROM users WHERE DiscordID = '{}'".format(str(id))))
        conn.commit()
        cur.close()
        conn.close()
        self.upload(self.SQLITE_FILE)

    def find_user_in_db(self, ServerOrDiscord, data):
        """
        Get DiscordID ('Discord')/PlexUsername ('Plex') (PlexOrDiscord) of PlexUsername/DiscordID (data)
        """
        self.download(self.SQLITE_FILE)
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        if self.PLATFORM == 'Plex':
            # Find Plex User -> Username, Note, ServerNum
            query = "SELECT {getWhat} FROM users WHERE {whereWhat} = '{data}'".format(
                getWhat=("PlexUsername, Note" + (
                    ", ServerNum" if self.MULTI_PLEX else "") if ServerOrDiscord is not 'Discord' else "DiscordID"),
                whereWhat=("DiscordID" if ServerOrDiscord is not 'Discord' else "PlexUsername"),
                data=str(data))
        else:
            # Find Jellyfin/Emby User -> ID
            query = "SELECT {getWhat} FROM users WHERE {whereWhat} = '{data}'".format(
                getWhat=("{}ID".format(self.PLATFORM) if ServerOrDiscord is not 'Discord' else "DiscordID"),
                whereWhat=("DiscordID" if ServerOrDiscord is not 'Discord' else "{}ID".format(self.PLATFORM)),
                data=str(data))
        cur.execute(str(query))
        results = cur.fetchone()
        cur.close()
        conn.close()
        self.upload(self.SQLITE_FILE)
        if results:
            return results if self.PLATFORM == 'Plex' else results[0]
            # returns [name, note], [name, note, number] or [id]
        else:
            if self.PLATFORM is not 'Plex':
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
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        query = "SELECT {}, Note FROM users WHERE {} = '{}'".format(
            ("{}Username".format(self.PLATFORM) if ServerOrDiscord is not 'Discord' else "DiscordID"),
            ("DiscordID" if ServerOrDiscord is not 'Discord' else "{}Username".format(self.PLATFORM)),
            str(data))
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
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        query = "SELECT * FROM users WHERE {} = '{}'".format(fieldType, str(data))
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
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        query = "SELECT * FROM users"
        cur.execute(query)
        result = cur.fetchall()
        cur.close()
        conn.close()
        self.upload(self.SQLITE_FILE)
        if result:
            return result
        return None

    def getWinners(self):
        """
        Get all users with 'w' note
        """
        self.download(self.SQLITE_FILE)
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        cur.execute("SELECT {} FROM users WHERE Note = 'w'".format(
            'PlexUsername' if self.PLATFORM == 'Plex' else "{}ID".format(self.PLATFORM)))
        results = cur.fetchall()
        cur.close()
        conn.close()
        self.upload(self.SQLITE_FILE)
        return results

    def getTrials(self):
        self.download(self.SQLITE_FILE)
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        query = "SELECT DiscordID FROM users WHERE ExpirationStamp<={} AND Note = 't'".format(str(int(time.time())))
        cur.execute(str(query))
        results = cur.fetchall()
        cur.close()
        conn.close()
        self.upload(self.SQLITE_FILE)
        return results
