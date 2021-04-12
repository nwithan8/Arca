from sqlalchemy import create_engine, MetaData
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import helper.encryption as encryption

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
        self.meta = None
        self.session = None

        if self.encrypted and self.key_file:
            key = encryption.get_raw_key(self.key_file)
            self.url = f'sqlite+pysqlcipher://:{key}@/{sqlite_file}?cipher=aes-256-cfb&kdf_iter=64000'
        else:
            self.url = f'sqlite:///{sqlite_file}'

        self.setup()

    def commit(self):
        self.session.commit()

    def close(self):
        self.session.close()

    def setup(self):
        if not self.url:
            return

        self.engine = create_engine(self.url)

        if not self.engine:
            return

        if not database_exists(self.engine.url):
            create_database(self.engine.url)

        self.base = declarative_base(bind=self.engine)
        self.meta = MetaData()
        self.meta.create_all(self.engine)

        Session = sessionmaker()
        Session.configure(bind=self.engine)
        self.session = Session()