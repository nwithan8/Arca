import json

from discord.ext import commands

from media_server.database.database import DiscordMediaServerConnectorDatabase

from settings import settings as arca_settings
import helper.discord_helper as discord_helper
from media_server.plex import settings as plex_settings
from media_server.plex import plex_api as px_api
from media_server.jellyfin import jellyfin_api as jf_api

def _read_file(file_path: str):
    with open(file_path) as f:
        return f.read()

def _read_file_lines(file_path: str):
    with open(file_path) as f:
        return f.readlines()

def _read_json_file(file_path: str):
    with open(file_path) as f:
        return json.load(f)

def get_discord_server_database(ctx: commands.Context):
    server_id = discord_helper.server_id(ctx=ctx)
    db_file_path = f"{arca_settings.ROOT_FOLDER}/databases/media_server/{server_id}.db"
    return DiscordMediaServerConnectorDatabase(sqlite_file=db_file_path,
                                               encrypted=False,
                                               media_server_type="plex",
                                               trial_length=plex_settings.TRIAL_LENGTH,
                                               multi_plex=False)

def get_plex_credentials(ctx: commands.Context):
    server_id = discord_helper.server_id(ctx=ctx)
    plex_credentials_path = f"{arca_settings.ROOT_FOLDER}/credentials/plex/admin/{server_id}.json"
    return _read_json_file(plex_credentials_path)

def get_plex_api(ctx: commands.Context):
    database = get_discord_server_database(ctx=ctx)
    creds = get_plex_credentials(ctx=ctx)
    return px_api.PlexConnections(plex_credentials=creds, database=database)

def get_jellyfin_credentials(ctx: commands.Context):
    server_id = discord_helper.server_id(ctx=ctx)
    jellyfin_credentials_path = f"{arca_settings.ROOT_FOLDER}/credentials/jellyfin/admin/{server_id}.json"
    return _read_json_file(jellyfin_credentials_path)

def get_jellyfin_api(ctx: commands.Context):
    server_id = discord_helper.server_id(ctx=ctx)
    database = get_discord_server_database(ctx=ctx)
    creds = get_jellyfin_credentials(ctx=ctx)
    jellyfin_token_path = f"{arca_settings.ROOT_FOLDER}/credentials/jellyfin/admin/{server_id}.token"
    return jf_api.JellyfinInstance(jellyfin_credentials=creds,
                                   jellyfin_token_file_path=jellyfin_token_path,
                                   database=database)