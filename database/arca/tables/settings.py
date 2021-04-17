from database.tools import *

class BotSettings(Base):
    __tablename__ = "settings"
    DiscordServerID = Column(Integer, primary_key=True)
    Prefix = Column(String)

    @none_as_null
    def __init__(self,
                 discord_id: int,
                 prefix: str):
        self.DiscordServerID = discord_id
        self.Prefix = prefix