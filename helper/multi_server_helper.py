import discord
from discord.ext import commands, tasks
import asyncio
import sqlite3
import time
import os
import helper.db_commands as db
import admin.settings as settings
import helper.encryption as encryption
import string
from helper.cog_list import nicks_to_paths, database_ignore

MULTIPLE_SERVERS = settings.MULTIPLE_SERVERS

CREATE_DISCORD_CONNECTOR_SQL = [
    "CREATE TABLE IF NOT EXISTS plex (DiscordID VARCHAR(100) NOT NULL, PlexUsername VARCHAR(100) NOT NULL, "
    "Email VARCHAR(100), ExpirationStamp INT(11), WhichPlexServer INT(11), WhichTautServer INT(11), PayMethod "
    "VARCHAR(5), SubType VARCHAR(5))",
    "CREATE TABLE IF NOT EXISTS jellyfin (DiscordID VARCHAR(100) NOT NULL, JellyfinUsername VARCHAR(100), JellyfinID "
    "VARCHAR(200) NOT NULL, ExpirationStamp INT(11), PayMethod VARCHAR(5), SubType VARCHAR(5))",
    "CREATE TABLE IF NOT EXISTS emby (DiscordID VARCHAR(100) NOT NULL, EmbyUsername VARCHAR(100), EmbyID VARCHAR(200) "
    "NOT NULL, ExpirationStamp INT(11), PayMethod VARCHAR(5), SubType VARCHAR(5))",
    "CREATE TABLE IF NOT EXISTS blacklist(IDorUsername VARCHAR(200))"
]

DISABLED_COG_MESSAGE = 'This command is disabled.'
ADMIN_CONFIG_REMINDER = 'DM me for configuration.'


def table_exists(table_name):
    database = db.DB(SQLITE_FILE=settings.CONFIG_DATABASE, ENCRYPTED=settings.DATABASE_ENCRYPTED,
                     KEY_FILE=settings.DATABASE_KEY_FILE)
    results = database.custom_query(
        queries=[f"SELECT name FROM sqlite_master WHERE type='table' and name='{table_name}'"],
        commit=False)
    if results:  # len > 0
        return True
    return False  # len = 0


def listing_exists(guild_id, table_name):
    database = db.DB(SQLITE_FILE=settings.CONFIG_DATABASE, ENCRYPTED=settings.DATABASE_ENCRYPTED,
                     KEY_FILE=settings.DATABASE_KEY_FILE)
    results = database.custom_query(queries=[f"SELECT * FROM {table_name} WHERE ServerID = {guild_id}"],
                                    commit=False)
    if results:  # len > 0
        return True
    return False  # len = 0


def is_admin(ctx):
    return ctx.message.author.server_permissions.administrator


def is_admin_dm_check(guild_id, user_id):
    try:
        database = db.DB(SQLITE_FILE=settings.CONFIG_DATABASE, ENCRYPTED=settings.DATABASE_ENCRYPTED,
                         KEY_FILE=settings.DATABASE_KEY_FILE)
        result = database.custom_query(queries=[f"SELECT ServerAdminID FROM servers WHERE ServerID = {guild_id}"],
                                       commit=False)
        if result and result != 'Error' and result[0][0]:
            return int(result[0][0]) == user_id
    except Exception as e:
        print(f"Error in is_admin_dm_check: {e}")
    return False


def is_admin_set(guild_id):
    try:
        database = db.DB(SQLITE_FILE=settings.CONFIG_DATABASE, ENCRYPTED=settings.DATABASE_ENCRYPTED,
                         KEY_FILE=settings.DATABASE_KEY_FILE)
        result = database.custom_query(queries=[f"SELECT ServerAdminID FROM servers WHERE ServerID = {guild_id}"],
                                       commit=False)
        print(result)
        if result and result != 'Error' and result[0][0]:
            return True
    except Exception as e:
        print(f"Error in is_admin_set: {e}")
    return False


def set_admin(guild_id, user_id):
    try:
        database = db.DB(SQLITE_FILE=settings.CONFIG_DATABASE, ENCRYPTED=settings.DATABASE_ENCRYPTED,
                         KEY_FILE=settings.DATABASE_KEY_FILE)
        result = database.custom_query(
            queries=[f"UPDATE servers SET ServerAdminID = {user_id} WHERE ServerID = {guild_id}"],
            commit=True)
        if result:
            return True
    except Exception as e:
        print(f"Error in set_admin: {e}")
    return False


def create_listing(guild_id, guild=None):
    try:
        database = db.DB(SQLITE_FILE=settings.CONFIG_DATABASE, ENCRYPTED=settings.DATABASE_ENCRYPTED,
                         KEY_FILE=settings.DATABASE_KEY_FILE)
        # blindly set up tables. May fail because already exist, that's fine.
        configure_servers_table()
        configure_cog_table()
        if guild:
            guild_id = guild.id
            success = database.custom_query(
                queries=[f"INSERT INTO servers (ServerName, ServerID) VALUES ({guild.name}, {guild_id})"], commit=True)
        else:
            success = database.custom_query(queries=[f"INSERT INTO servers (ServerID) VALUES ({guild_id})"],
                                            commit=True)
        if success:
            if database.custom_query(queries=[f'INSERT INTO cogs (ServerID) VALUES ({guild_id})'], commit=True):
                if database.custom_query(queries=[f'INSERT INTO configs (ServerID) VALUES ({guild_id}'], commit=True):
                    if enable_all_cogs(guild_id=guild_id):
                        return True
    except Exception as e:
        print(f"Error in create_listing: {e}")
    return False


def get_all_cogs_from_config(guild_id):
    database = db.DB(SQLITE_FILE=settings.CONFIG_DATABASE, ENCRYPTED=settings.DATABASE_ENCRYPTED,
                     KEY_FILE=settings.DATABASE_KEY_FILE)
    return database.custom_query(queries=[f"SELECT * FROM cogs WHERE ServerID = {guild_id}"], commit=False)


def configure_servers_table():
    try:
        database = db.DB(SQLITE_FILE=settings.CONFIG_DATABASE, ENCRYPTED=settings.DATABASE_ENCRYPTED,
                         KEY_FILE=settings.DATABASE_KEY_FILE)
        if not table_exists(table_name='servers'):
            if database.custom_query(queries=[
                f"CREATE TABLE servers (ServerName VARCHAR(1000), ServerID INT(100) PRIMARY KEY UNIQUE, ServerAdminID "
                f"INT(100))"], commit=True):
                return True
    except Exception as e:
        print(f"Error in configure_servers_table: {e}")
    return False


def configure_cog_table():
    try:
        database = db.DB(SQLITE_FILE=settings.CONFIG_DATABASE, ENCRYPTED=settings.DATABASE_ENCRYPTED,
                         KEY_FILE=settings.DATABASE_KEY_FILE)
        if not table_exists(table_name='cogs'):
            database.custom_query(queries=[f"CREATE TABLE cogs (ServerID INT(100))"], commit=True)
        existing_columns = get_table_column_names(table_name='cogs')
        print(existing_columns)
        for cog_name in nicks_to_paths.keys():
            if cog_name not in existing_columns and cog_name not in database_ignore:
                database.custom_query(queries=[f"ALTER TABLE cogs ADD COLUMN {cog_name} INT(1)"], commit=True)
        return True
    except Exception as e:
        print(f"Error in configure_cog_table: {e}")
    return False


def enable_all_cogs(guild_id):
    try:
        database = db.DB(SQLITE_FILE=settings.CONFIG_DATABASE, ENCRYPTED=settings.DATABASE_ENCRYPTED,
                         KEY_FILE=settings.DATABASE_KEY_FILE)
        allowed_cogs = []
        for cog_name in nicks_to_paths.keys():
            if cog_name not in database_ignore:
                allowed_cogs.append(cog_name)
        cog_update_list = " = 1, ".join(allowed_cogs) + " = 1"
        results = database.custom_query(queries=[f"UPDATE cogs SET {cog_update_list} WHERE ServerID = {guild_id}"],
                                        commit=True)
        print(results)
        if results:
            return True
    except Exception as e:
        print(f"Error in enable_all_cogs: {e}")
    return False


def enable_cog(guild_id, cog_name):
    try:
        database = db.DB(SQLITE_FILE=settings.CONFIG_DATABASE, ENCRYPTED=settings.DATABASE_ENCRYPTED,
                         KEY_FILE=settings.DATABASE_KEY_FILE)
        return database.custom_query(queries=[f"UPDATE cogs SET {cog_name} = 1 WHERE ServerID = {guild_id}"],
                                     commit=True)
    except Exception as e:
        return False
        # raise Exception("Couldn't enable cog.")


def disable_cog(guild_id, cog_name):
    try:
        database = db.DB(SQLITE_FILE=settings.CONFIG_DATABASE, ENCRYPTED=settings.DATABASE_ENCRYPTED,
                         KEY_FILE=settings.DATABASE_KEY_FILE)
        return database.custom_query(queries=[f"UPDATE cogs SET {cog_name} = NULL WHERE ServerID = {guild_id}"],
                                     commit=True)
    except Exception as e:
        return False
        # raise Exception("Couldn't disable cog.")


def initialize_media_server_config(guild_id, server_type, cog_settings={}):
    try:
        database = db.DB(SQLITE_FILE=settings.CONFIG_DATABASE, ENCRYPTED=settings.DATABASE_ENCRYPTED,
                         KEY_FILE=settings.DATABASE_KEY_FILE)
        return database.custom_query(
            queries=[f"INSERT INTO configs ({server_type}Settings) VALUES {cog_settings} WHERE ServerID = {guild_id}"],
            commit=True)
    except Exception as e:
        return False
        # raise Exception("Couldn't disable cog.")


def get_example_config(cog_name):
    database = db.DB(SQLITE_FILE=settings.CONFIG_DATABASE, ENCRYPTED=settings.DATABASE_ENCRYPTED,
                     KEY_FILE=settings.DATABASE_KEY_FILE)
    res = database.custom_query(queries=[f"SELECT {cog_name}Settings FROM configs"],
                                commit=False)
    if res and res != 'Error':
        return res[0]
    return None


def get_whole_media_server_config(guild_id, server_type):
    database = db.DB(SQLITE_FILE=settings.CONFIG_DATABASE, ENCRYPTED=settings.DATABASE_ENCRYPTED,
                     KEY_FILE=settings.DATABASE_KEY_FILE)
    return database.custom_query(queries=[f"SELECT {server_type}Settings FROM configs WHERE ServerID = {guild_id}"],
                                 commit=False)


def get_partial_media_server_config(guild_id, server_type, setting_name):
    database = db.DB(SQLITE_FILE=settings.CONFIG_DATABASE, ENCRYPTED=settings.DATABASE_ENCRYPTED,
                     KEY_FILE=settings.DATABASE_KEY_FILE)
    return database.custom_query(queries=[
        f"SELECT json_extract({server_type}Settings, '$.{setting_name}') FROM configs WHERE ServerID = {guild_id}"],
        commit=False)


def edit_media_server_config(guild_id, server_type, setting_name, setting_value):
    database = db.DB(SQLITE_FILE=settings.CONFIG_DATABASE, ENCRYPTED=settings.DATABASE_ENCRYPTED,
                     KEY_FILE=settings.DATABASE_KEY_FILE)
    if isinstance(setting_value, int) or isinstance(setting_value, float):  # don't use quotes around setting value
        return database.custom_query(queries=[
            f"SELECT json_set({server_type}Settings, '$.{setting_name}', {setting_value}) from configs WHERE ServerID = {guild_id}"],
            commit=True)
    return database.custom_query(queries=[
        f"SELECT json_set({server_type}Settings, '$.{setting_name}', '{setting_value}') from configs WHERE ServerID = {guild_id}"],
        commit=True)


def get_table_column_names(table_name):
    database = db.DB(SQLITE_FILE=settings.CONFIG_DATABASE, ENCRYPTED=settings.DATABASE_ENCRYPTED,
                     KEY_FILE=settings.DATABASE_KEY_FILE)
    return database.custom_query(
        queries=[f"PRAGMA table_info([{table_name}])"],
        commit=False)


def create_discord_connector(guild_id):
    try:
        if not os.path.exists(f'media_server/databases/{guild_id}.db.crypt'):
            if not os.path.exists(f'media_server/databases/{guild_id}.key'):
                encryption.getKey(key_file=f'media_server/databases/{guild_id}.key')  # create and save new key
            new_database = db.DB(SQLITE_FILE=f'media_server/databases/{guild_id}.db.crypt', ENCRYPTED=True,
                                 KEY_FILE=f'media_server/databases/{guild_id}.key')
            print(new_database.custom_query(queries=CREATE_DISCORD_CONNECTOR_SQL, commit=True))
        return True
    except Exception as e:
        print(e)
        return False


def get_discord_connector(guild_id):
    if os.path.exists(f'media_server/databases/{guild_id}.db.crypt') and os.path.exists(
            f'media_server/databases/{guild_id}.key'):
        return f'media_server/databases/{guild_id}.db.crypt'
    return None


def cog_is_enabled(guild_id, cog_name):
    try:
        database = db.DB(SQLITE_FILE=settings.CONFIG_DATABASE, ENCRYPTED=settings.DATABASE_ENCRYPTED,
                         KEY_FILE=settings.DATABASE_KEY_FILE)
        result = database.custom_query(queries=[f"SELECT {cog_name} FROM cogs WHERE ServerID = {guild_id}"],
                                       commit=False)
        if result and result != 'Error' and result[0][0] == 1:
            return True
    except Exception as e:
        print(f"Error in cog_is_enabled: {e}")
    return False


def is_valid_cog(cog_name):
    try:
        database = db.DB(SQLITE_FILE=settings.CONFIG_DATABASE, ENCRYPTED=settings.DATABASE_ENCRYPTED,
                         KEY_FILE=settings.DATABASE_KEY_FILE)
        result = database.custom_query(queries=[f"SELECT {cog_name} FROM cogs"],
                                       commit=False)
        print(result)
        if result and result != 'Error':
            return True
    except Exception as e:
        print(f"Error in is_valid_cog: {e}")
    return False


def is_valid_setting(guild_id, setting_name, cog_name):
    try:
        database = db.DB(SQLITE_FILE=settings.CONFIG_DATABASE, ENCRYPTED=settings.DATABASE_ENCRYPTED,
                         KEY_FILE=settings.DATABASE_KEY_FILE)
        result = database.custom_query(queries=[
            f"SELECT json_extract({cog_name}Settings, '$.{setting_name}') FROM configs WHERE ServerID = {guild_id}"],
            commit=False)
        print(result)
        if result != 'Error':
            return True
    except Exception as e:
        print(f"Error in is_valid_setting: {e}")
    return False


def get_guild_from_name(guild_name, bot_instance):
    for g in bot_instance.guilds:
        if g.name == guild_name:
            return g
    return None


def user_is_member_of_guild(guild, user_id):
    member = guild.get_member(user_id)
    if member:
        return True
    return False
