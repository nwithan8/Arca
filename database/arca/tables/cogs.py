from database.tools import *

class CogsEnabled(Base):
    __tablename__ = "cogs"
    DiscordServerID = Column(Integer, primary_key=True)
    CogName = Column(String)

    @none_as_null
    def __init__(self,
                 discord_id: int,
                 cog_name: str):
        self.DiscordServerID = discord_id
        self.CogName = cog_name