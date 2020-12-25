import sqlite3
import time
from typing import List, Union

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import helper.dropbox_handler as dbx
import helper.encryption as encryption


def unlock(database, key_file):
    key = encryption.get_raw_key(key_file)
    if key:
        database.execute(f'pragma key="{key}"')
        return True
    print("Couldn't get the key to unlock the database_handler.")
    return False


class Table:
    def __init__(self, name: str, database_connection):
        self.name = name
        self.database = database_connection

    @property
    def describe(self):
        try:
            conn = self.database._crypt_check()
            cur = conn.cursor()
            cur.execute("PRAGMA table_info([{}])".format(self.name))
            result = cur.fetchall()
            cur.close()
            conn.close()
            return result
        except:
            raise Exception

class ColumnValuePair:
    def __init__(self, column_name: str, value, comparison: str = "="):
        self.column = column_name
        self.value = value
        self.comparison = comparison

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        if type(self.value) == str:
            self.value = f"'{self.value}'"
        return f"{self.column} {self.comparison} {self.value}"

class InsertString:
    def __init__(self, insert_pairs: List[ColumnValuePair]):
        self.pairs = insert_pairs

    def __str__(self):
        return f"({','.join(pair.column for pair in self.pairs)}) VALUES ({','.join(pair.value for pair in self.pairs)})"

class WhereString:
    def __init__(self, where_pairs: List[ColumnValuePair]):
        self.wheres = where_pairs

    def __str__(self):
        return " and ".join(pair.__str__() for pair in self.wheres)

class UpdateString:
    def __init__(self, update_pairs: List[ColumnValuePair]):
        self.pairs = update_pairs

    def __str__(self):
        return ', '.join(pair.__str__() for pair in self.pairs)

class SelectQuery:
    def __init__(self,
                 database_connection,
                 column_names: List[str],
                 from_table: str,
                 where: List[ColumnValuePair] = None):
        self.columns = column_names
        self.table = from_table
        self.where = WhereString(where_pairs=where).__str__() if where else ""
        self.database = database_connection

    @property
    def string(self):
        return self.__str__()

    # TODO What does this return? String, list of string, tuple?
    def execute(self, fetch_all: bool = False):
        try:
            conn = self.database._crypt_check()
            cur = conn.cursor()
            cur.execute(self.string)
            if fetch_all:
                result = cur.fetchall()
            else:
                result = cur.fetchone()
            cur.close()
            conn.close()
            return result
        except:
            raise Exception

    def __str__(self):
        return f"SELECT {', '.join(column for column in self.columns)} FROM {self.table} {self.where}"

class DeleteQuery:
    def __init__(self,
                 database_connection,
                 from_table: str,
                 where: List[ColumnValuePair] = None):
        self.table = from_table
        self.where = WhereString(where_pairs=where).__str__() if where else ""
        self.database = database_connection

    @property
    def string(self):
        return self.__str__()

    def execute(self) -> bool:
        try:
            conn = self.database._crypt_check()
            cur = conn.cursor()
            cur.execute(self.string)
            conn.commit()
            cur.close()
            conn.close()
            return True
        except:
            raise Exception

    def __str__(self):
        return f"DELETE FROM {self.table} {self.where}"

class InsertQuery:
    def __init__(self,
                 database_connection,
                 column_value_pairs: List[ColumnValuePair],
                 into_table: str):
        self.table = into_table
        self.values = InsertString(insert_pairs=column_value_pairs)
        self.database = database_connection

    @property
    def string(self):
        return self.__str__()

    def execute(self) -> bool:
        try:
            result = False
            conn = self.database._crypt_check()
            cur = conn.cursor()
            cur.execute(self.string)
            if int(cur.rowcount) > 0:
                result = True
            conn.commit()
            cur.close()
            conn.close()
            return result
        except:
            raise Exception

    def __str__(self):
        return f"INSERT INTO {self.table} {self.values}"

class UpdateQuery:
    def __init__(self,
                 database_connection,
                 table_name: str,
                 column_value_pairs: List[ColumnValuePair],
                 where: List[ColumnValuePair]):
        self.table = table_name
        self.values = UpdateString(update_pairs=column_value_pairs).__str__()
        self.where = WhereString(where_pairs=where).__str__() if where else ""
        self.database = database_connection
        self.where = WhereString(where_pairs=where).__str__() if where else ""

    @property
    def string(self):
        return self.__str__()

    def execute(self) -> bool:
        try:
            result = False
            conn = self.database._crypt_check()
            cur = conn.cursor()
            cur.execute(self.string)
            if int(cur.rowcount) > 0:
                result = True
            conn.commit()
            cur.close()
            conn.close()
            return result
        except:
            raise Exception

    def __str__(self):
        return f"UPDATE {self.table} SET {self.values} {self.where}"


class Database:
    def __init__(self,
                 sqlite_file: str,
                 encrypted: bool = False,
                 key_file: str = None,
                 use_dropbox: bool = False):
        self.sqlite_file = sqlite_file
        self.use_dropbox = use_dropbox
        self.encrypted = encrypted
        self.key_file = key_file
        if self.encrypted and not self.key_file:
            raise Exception("Missing KEY_FILE to unlock encrypted database_handler.")
        self._tables = []

    def _crypt_check(self, file = None):
        if not file:
            file = self.sqlite_file
        if self.encrypted:
            from pysqlcipher3 import dbapi2 as sqlcipher
            db = sqlcipher.connect(file)
            if unlock(db, self.key_file):
                return db
            return None
        return sqlite3.connect(file)

    def download(self, file):
        if self.use_dropbox and file:
            return dbx.download_file(file)
        return False

    def upload(self, file):
        if self.use_dropbox and file:
            return dbx.upload_file(file)
        return False

    def backup(self, file, rename=False):
        if self.use_dropbox and file:
            return dbx.upload_file(filePath=file, rename=rename)
        return False

    @property
    def tables(self):
        # only works on SQLite3
        if not self._tables:
            self._tables = []
            command = SelectQuery(column_names=["name"], from_table="sqlite_master", where=[ColumnValuePair(column_name="type", value="table")], database_connection=self)
            results = command.execute(fetch_all=True)
            for table_name in results:
                self._tables.append(Table(name=table_name, database_connection=self))
        return self._tables


class SQLAlchemyDatabase:
    def __init__(self,
                 sqlite_file: str,
                 encrypted: bool = False,
                 key_file: str = None,
                 use_dropbox: bool = False):
        self.sqlite_file = sqlite_file
        self.use_dropbox = use_dropbox
        self.encrypted = encrypted
        self.key_file = key_file
        if self.encrypted and not self.key_file:
            raise Exception("Missing KEY_FILE to unlock encrypted database_handler.")

        self.engine = None
        self.base = None
        self.session = None

        if self.encrypted and self.key_file:
            key = encryption.get_raw_key(self.key_file)
            self.engine = create_engine(f'sqlite+pysqlcipher://:{key}@/{sqlite_file}?cipher=aes-256-cfb&kdf_iter=64000')
        else:
            self.engine = create_engine(f'sqlite:///{sqlite_file}')
        self.base = declarative_base(bind=self.engine)
        Session = sessionmaker()
        Session.configure(bind=self.engine)
        self.session = Session()

    def commit(self):
        self.session.commit()
