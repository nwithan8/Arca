class DiscordUser:
    def __init__(self,
                 username: str = None,
                 id: int = None):
        self.username = username
        self.id = id

class MediaServerUser:
    def __init__(self,
                 discord_id: int = None,
                 discord_username: str = None,
                 media_server_username: str = None,
                 media_server_id=None,
                 user_type: str = None):
        self.discord_user = DiscordUser(username=discord_username, id=discord_id)
        self.media_username = media_server_username
        self.media_id = media_server_id
        self.user_type = user_type

class PlexUser:
    def __init__(self,
                 username: str = None,
                 user_type: str = None,
                 server_number: int = None):
        self.username = username
        self.user_type = user_type
        self.server_number = server_number

class EmbyJellyfinUser:
    def __init__(self,
                 username: str = None,
                 id: str = None,
                 user_type: str = None):
        self.username = username
        self.id = id
        self.user_type = user_type


class EmbyUser(EmbyJellyfinUser):
    def __init__(self,
                 username: str = None,
                 user_type: str = None,
                 id: str = None):
        super().__init__(username, id, user_type)

class JellyfinUser(EmbyJellyfinUser):
    def __init__(self,
                 username: str = None,
                 user_type: str = None,
                 id: str = None):
        super().__init__(username, id, user_type)
