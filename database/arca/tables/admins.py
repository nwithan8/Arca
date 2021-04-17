from database.tools import *

class DiscordAdmins(Base):
    __tablename__ = "admins"
    DiscordServerID = Column(Integer, primary_key=True)
    DiscordAdminID = Column(Integer, nullable=True)
    DiscordAdminRole = Column(Integer, nullable=True)

    @none_as_null
    def __init__(self,
                 discord_id: int,
                 admin_id: int = None,
                 admin_role: str = None):
        if not admin_role and not admin_id:
            raise Exception("Must provide either admin role or admin ID when adding an admin to database.")
        self.DiscordServerID = discord_id
        self.DiscordAdminID = admin_id
        self.DiscordAdminRole = admin_role