import sqlite3
import time
import emby.settings as settings

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

    def add_user_to_db(self, DiscordId, EmbyName, EmbyId, note):
        self.download()
        result = False
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        if note == 't':
            timestamp = int(time.time()) + self.TRIAL_LENGTH
            query = "INSERT OR IGNORE INTO users (DiscordID, EmbyUsername, EmbyID, ExpirationStamp, " \
                    "Note) VALUES ('{did}', '{eu}', '{eid}', '{time}', '{note}')".format(
                did=str(DiscordId),
                eu=str(EmbyName),
                eid=str(EmbyId),
                time=str(timestamp),
                note=str(note)
            )
            cur.execute(str(query))
            query = "UPDATE users SET ExpirationStamp = '{time}' WHERE EmbyID = '{eid}'".format(
                time=str(timestamp),
                eid=str(EmbyId)
            )
        else:
            query = "INSERT OR IGNORE INTO users (DiscordID, EmbyUsername, EmbyID, Note) VALUES ('{did}', " \
                    "'{eu}', '{eid}', '{note}')".format(
                did=str(DiscordId),
                eu=str(EmbyName),
                eid=str(EmbyId),
                note=str(note)
            )
        cur.execute(str(query))
        print(cur.rowcount)
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

    def find_user_in_db(self, EmbyOrDiscord, data):
        """
        Returns EmbyID/DiscordID
        """
        self.download()
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        query = "SELECT {} FROM users WHERE {} = '{}'".format((
            "EmbyID" if EmbyOrDiscord == "Emby" else "DiscordID"), (
            "DiscordID" if EmbyOrDiscord == "Emby" else "EmbyID"), str(data))
        cur.execute(str(query))
        result = cur.fetchone()
        cur.close()
        conn.close()
        self.upload()
        if result:
            return result[0]
        else:
            return None

    def find_username_in_db(self, EmbyOrDiscord, data):
        """
        Returns EmbyUsername/DiscordID, Note
        """
        self.download()
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        query = "SELECT {}, Note FROM users WHERE {} = '{}'".format((
            "EmbyUsername" if EmbyOrDiscord == "Emby" else "DiscordID"), (
            "DiscordID" if EmbyOrDiscord == "Emby" else "EmbyUsername"), str(data))
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
        cur.execute("SELECT EmbyID FROM users WHERE Note = 'w'")
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
