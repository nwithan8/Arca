import sqlite3
import time


class DB:
    def __init__(self, SQLITE_FILE, TRIAL_LENGTH):
        self.SQLITE_FILE = SQLITE_FILE
        self.TRIAL_LENGTH = TRIAL_LENGTH

    def describe_table(self, table):
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        cur.execute("PRAGMA  table_info([{}])".format(str(table)))
        result = cur.fetchall()
        cur.close()
        conn.close()
        if result:
            return result
        else:
            return None

    def add_user_to_db(self, DiscordId, JellyfinName, JellyfinId, note):
        result = False
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        if note == 't':
            timestamp = int(time.time()) + (3600 * self.TRIAL_LENGTH)
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
        return result

    def remove_user_from_db(self, uid):
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        cur.execute(str("DELETE FROM users WHERE DiscordID = '{}'".format(str(uid))))
        conn.commit()
        cur.close()
        conn.close()

    def find_user_in_db(self, JellyfinOrDiscord, data):
        """
        Returns JellyfinID/DiscordID
        """
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        query = "SELECT {} FROM users WHERE {} = '{}'".format((
            "JellyfinID" if JellyfinOrDiscord == "Jellyfin" else "DiscordID"), (
                    "DiscordID" if JellyfinOrDiscord == "Jellyfin" else "JellyfinID"), str(data))
        cur.execute(str(query))
        result = cur.fetchone()
        cur.close()
        conn.close()
        if result:
            return result[0]
        else:
            return None

    def find_username_in_db(self, JellyfinOrDiscord, data):
        """
        Returns JellyfinUsername/DiscordID, Note
        """
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        query = "SELECT {}, Note FROM users WHERE {} = '{}'".format((
            "JellyfinUsername" if JellyfinOrDiscord == "Jellyfin" else "DiscordID"), (
                    "DiscordID" if JellyfinOrDiscord == "Jellyfin" else "JellyfinUsername"), str(data))
        cur.execute(str(query))
        result = cur.fetchone()
        cur.close()
        conn.close()
        if result:
            return result[0], result[1]
        else:
            return None, None

    def find_entry_in_db(self, type, data):
        """
        Returns whole entry
        """
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        query = "SELECT * FROM users WHERE {} = '{}'".format(type, str(data))
        cur.execute(query)
        result = cur.fetchone()
        cur.close()
        conn.close()
        if result:
            return result
        else:
            return None

    def get_all_entries_in_db(self):
        """
        Returns all database entries
        """
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        query = "SELECT * FROM users"
        cur.execute(query)
        result = cur.fetchall()
        cur.close()
        conn.close()
        if result:
            return result
        else:
            return None
