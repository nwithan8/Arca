from discord.ext import commands

from helper.utils import read_json_file
from database.media_servers.media_server_database import DiscordMediaServerConnectorDatabase

import helper.discord_helper as discord_helper
from media_server.plex import settings as plex_settings
from media_server.plex import plex_api as px_api
from media_server.jellyfin import jellyfin_api as jf_api
from discord_cogs.upgradeChat import upgrade_chat_api as uc_api
from settings.global_settings import DEFAULT_PREFIX


def get_bot_prefix(bot, message):
    if not hasattr(bot, "settings_database"):
        return DEFAULT_PREFIX
    return bot.settings_database.get_prefix(discord_server_id=message.guild.id)

def get_discord_server_database(ctx: commands.Context):
    server_id = discord_helper.server_id(ctx=ctx)
    db_file_path = f"databases/media_server/{server_id}.db"
    return DiscordMediaServerConnectorDatabase(sqlite_file=db_file_path,
                                               encrypted=False,
                                               media_server_type="plex",
                                               trial_length=plex_settings.TRIAL_LENGTH,
                                               multi_plex=False)

def get_plex_credentials(ctx: commands.Context):
    server_id = discord_helper.server_id(ctx=ctx)
    plex_credentials_path = f"credentials/plex/admin/{server_id}.json"
    return read_json_file(plex_credentials_path)

def get_plex_api(ctx: commands.Context):
    database = get_discord_server_database(ctx=ctx)
    creds = get_plex_credentials(ctx=ctx)
    return px_api.PlexConnections(plex_credentials=creds, database=database)

def get_jellyfin_credentials(ctx: commands.Context):
    server_id = discord_helper.server_id(ctx=ctx)
    jellyfin_credentials_path = f"credentials/jellyfin/admin/{server_id}.json"
    return read_json_file(jellyfin_credentials_path)

def get_jellyfin_api(ctx: commands.Context):
    server_id = discord_helper.server_id(ctx=ctx)
    database = get_discord_server_database(ctx=ctx)
    creds = get_jellyfin_credentials(ctx=ctx)
    jellyfin_token_path = f"credentials/jellyfin/admin/{server_id}.token"
    return jf_api.JellyfinInstance(jellyfin_credentials=creds,
                                   jellyfin_token_file_path=jellyfin_token_path,
                                   database=database)

def get_upgrade_chat_credentials(ctx: commands.Context):
    server_id = discord_helper.server_id(ctx=ctx)
    upgrade_chat_credentials_path = f"credentials/upgradeChat/admin/{server_id}.json"
    return read_json_file(upgrade_chat_credentials_path)

def get_upgrade_chat_api(ctx: commands.Context):
    creds = get_upgrade_chat_credentials(ctx=ctx)
    return uc_api.UpgradeChatInstance(upgrade_chat_credentials=creds)


def load_api(ctx: commands.Context, api_type: str):
    if api_type == "plex":
        return get_plex_api(ctx=ctx)
    elif api_type == "jellyfin":
        return get_jellyfin_api(ctx=ctx)
    elif api_type == "upgradeChat":
        return get_upgrade_chat_api(ctx=ctx)
    else:
        return None