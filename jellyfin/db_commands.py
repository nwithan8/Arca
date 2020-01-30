import sqlite3
import time
import jellyfin.settings as settings

if settings.USE_DROPBOX:
    import helper.dropbox_handler as dbx


class DB:
    def __init__(self, SQLITE_FILE, TRIAL_LENGTH):
        self.SQLITE_FILE = SQLITE_FILE
        self.TRIAL_LENGTH = TRIAL_LENGTH

    def download(self):
        if settings.USE_DROPBOX:
            return dbx.download_file(self.SQLITE_FILE)
        return True

    def upload(self):
        if settings.USE_DROPBOX:
            return dbx.upload_file(self.SQLITE_FILE)
        return True

    def describe_table(self, table):
        self.download()
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        cur.execute("PRAGMA  table_info([{}])".format(str(table)))
        result = cur.fetchall()
        cur.close()
        conn.close()
        self.upload()
        if result:
            return result
        else:
            return None

    def add_user_to_db(self, DiscordId, JellyfinName, JellyfinId, note):
        self.download()
        result = False
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        if note == 't':
            timestamp = int(time.time()) + self.TRIAL_LENGTH
            query = "INSERT OR IGNORE INTO users (DiscordID, JellyfinUsername, JellyfinID, ExpirationStamp, " \
                    "Note) VALUES ('{did}', '{ju}', '{jid}', '{time}', '{note}')".format(
                did=str(DiscordId), ju=str(JellyfinName), jid=str(JellyfinId), time=str(timestamp), note=str(note))
            cur.execute(str(query))
            query = "UPDATE users SET ExpirationStamp = '{time}' WHERE JellyfinID = '{jid}'".format(time=str(timestamp),
                                                                                                    jid=str(JellyfinId))
        else:
            query = "INSERT OR IGNORE INTO users (DiscordID, JellyfinUsername, JellyfinID, Note) VALUES ('{did}', " \
                    "'{ju}', '{jid}', '{note}')".format(
                did=str(DiscordId), ju=str(JellyfinName), jid=str(JellyfinId), note=str(note))
        cur.execute(str(query))
        if int(cur.rowcount) > 0:
            result = True
        conn.commit()
        cur.close()
        conn.close()
        self.upload()
        return result

    def remove_user_from_db(self, uid):
        self.download()
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        cur.execute(str("DELETE FROM users WHERE DiscordID = '{}'".format(str(uid))))
        conn.commit()
        cur.close()
        conn.close()
        self.upload()

    def find_user_in_db(self, JellyfinOrDiscord, data):
        """
        Returns JellyfinID/DiscordID
        """
        self.download()
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        query = "SELECT {} FROM users WHERE {} = '{}'".format((
            "JellyfinID" if JellyfinOrDiscord == "Jellyfin" else "DiscordID"), (
                    "DiscordID" if JellyfinOrDiscord == "Jellyfin" else "JellyfinID"), str(data))
        cur.execute(str(query))
        result = cur.fetchone()
        cur.close()
        conn.close()
        self.upload()
        if result:
            return result[0]
        else:
            return None

    def find_username_in_db(self, JellyfinOrDiscord, data):
        """
        Returns JellyfinUsername/DiscordID, Note
        """
        self.download()
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        query = "SELECT {}, Note FROM users WHERE {} = '{}'".format((
            "JellyfinUsername" if JellyfinOrDiscord == "Jellyfin" else "DiscordID"), (
                    "DiscordID" if JellyfinOrDiscord == "Jellyfin" else "JellyfinUsername"), str(data))
        cur.execute(str(query))
        result = cur.fetchone()
        cur.close()
        conn.close()
        self.upload()
        if result:
            return result[0], result[1]
        else:
            return None, None

    def find_entry_in_db(self, type, data):
        """
        Returns whole entry
        """
        self.download()
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        query = "SELECT * FROM users WHERE {} = '{}'".format(type, str(data))
        cur.execute(query)
        result = cur.fetchone()
        cur.close()
        conn.close()
        self.upload()
        if result:
            return result
        else:
            return None

    def get_all_entries_in_db(self):
        """
        Returns all database entries
        """
        self.download()
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        query = "SELECT * FROM users"
        cur.execute(query)
        result = cur.fetchall()
        cur.close()
        conn.close()
        self.upload()
        if result:
            return result
        else:
            return None

    def getWinners(self):
        """
        Get all users with 'w' note
        """
        self.download()
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        cur.execute("SELECT JellyfinID FROM users WHERE Note = 'w'")
        results = cur.fetchall()
        cur.close()
        conn.close()
        self.upload()
        return results

    def getTrials(self):
        self.download()
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        query = "SELECT DiscordID FROM users WHERE ExpirationStamp<={} AND Note = 't'".format(str(int(time.time())))
        cur.execute(str(query))
        results = cur.fetchall()
        cur.close()
        conn.close()
        self.upload()
        return results