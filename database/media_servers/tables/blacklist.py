from database.tools import *

class BlacklistEntry(Base):
    __tablename__ = "blacklist"
    IDorUsername = Column(String(200), primary_key=True)

    def __init__(self, id_or_username: str):
        self.IDorUsername = id_or_username
