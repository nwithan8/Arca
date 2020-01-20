import sqlite3
import time


class DB:
    def __init__(self, SQLITE_FILE, MULTI_PLEX, TRIAL_LENGTH):
        self.SQLITE_FILE = SQLITE_FILE
        self.MULTI_PLEX = MULTI_PLEX
        self.TRIAL_LENGTH = TRIAL_LENGTH

    def describe_table(self, table):
        conn = sqlite3.connect(self.SQLITE_FILE)
        response = ""
        cur = conn.cursor()
        cur.execute("PRAGMA table_info([{name}])".format(table))
        response = cur.fetchall()
        cur.close()
        conn.close()
        return response

    def add_user_to_db(self, discordId, plexUsername, note, serverNumber=None):
        result = False
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        query = ""
        if note == 't':
            timestamp = int(time.time()) + self.TRIAL_LENGTH
            query = "INSERT OR IGNORE INTO users (DiscordID, PlexUsername, ExpirationStamp{serverNumOpt}, " \
                    "Note) VALUES ('{discordId}', '{plexUsername}', '{expirationStamp}'{serverNum}, '{note}')"\
                .format(serverNumOpt=(", ServerNum" if serverNumber is not None else ""), discordId=discordId, plexUsername=plexUsername, expirationStamp=str(timestamp), serverNum=((",'" + serverNumber + "'") if serverNumber else ""), note=str(note))
            cur.execute(str(query))
            query = "UPDATE users SET ExpirationStamp = '{} WHERE PlexUsername = '{}'".format(str(timestamp), str(plexUsername))
            # Awaiting SQLite 3.24 support/adoption to use cleaner UPSERT function
        else:
            query = "INSERT OR IGNORE INTO users (DiscordID, PlexUsername{serverNumOpt}, Note) VALUES ('{discordId}'," \
                    "'{plexUsername}'{serverNum}, '{note}')".format(serverNumOpt=(
                ", ServerNum" if serverNumber is not None else ""), discordId=str(discordId), plexUsername=str(
                plexUsername), serverNum=((",'" + str(serverNumber) + "'") if serverNumber is not None else ""), note=str(note))
        cur.execute(str(query))
        if int(cur.rowcount) > 0:
            result = True
        conn.commit()
        cur.close()
        conn.close()
        return result

    def remove_user_from_db(self, id):
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        cur.execute(str("DELETE FROM users WHERE DiscordID = '{}'".format(str(id))))
        conn.commit()
        cur.close()
        conn.close()

    def find_user_in_db(self, PlexOrDiscord, data):
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        query = "SELECT {getWhat} FROM users WHERE {whereWhat} = '{data}'".format(getWhat=("PlexUsername, Note" + (
            ", ServerNum" if self.MULTI_PLEX else "") if PlexOrDiscord == "Plex" else "DiscordID"), whereWhat=(
                    "DiscordID" if PlexOrDiscord == "Plex" else "PlexUsername"), data=str(data))
        cur.execute(str(query))
        results = cur.fetchone()
        cur.close()
        conn.close()
        if results:
            return results
            # return [name, note], [name, note, number] or [id]
        else:
            if PlexOrDiscord == "Plex":
                if self.MULTI_PLEX:
                    return None, None, None
                else:
                    return None, None
            else:
                return None

    def find_entry_in_db(self, type, data):
        """
        Returns whole entry
        """
        conn = sqlite3.connect(self.SQLITE_FILE)
        response = ""
        cur = conn.cursor()
        query = "SELECT * FROM users WHERE {} = '{}'".format(type, data)
        cur.execute(query)
        response = cur.fetchone()
        cur.close()
        conn.close()
        return response

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

    def getWinners(self):
        """
        Get all users with 'w' note
        """
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        cur.execute("SELECT PlexUsername FROM users WHERE Note = 'w'")
        results = cur.fetchall()
        cur.close()
        conn.close()
        return results

    def getTrials(self):
        conn = sqlite3.connect(self.SQLITE_FILE)
        cur = conn.cursor()
        query = "SELECT DiscordID FROM users WHERE ExpirationStamp<={} AND Note = 't'".format(str(int(time.time())))
        cur.execute(str(query))
        results = cur.fetchall()
        cur.close()
        conn.close()
        return results
