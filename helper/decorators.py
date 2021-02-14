import functools
from functools import wraps

import discord
from discord.ext.commands import NoPrivateMessage
from sqlalchemy import null


def none_as_null(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        """
        Replace None as null()
        """
        func(self, *args, **kwargs)
        for k, v in self.__dict__.items():
            if v is None:
                setattr(self, k, null())

    return wrapper


def has_admin_role(func):
    @wraps(func)
    def check(self, *args, **kwargs):
        ctx = kwargs['ctx']
        discord_server_id = ctx.message.guild.id
        admin_role_names = self.bot.settings_database.get_admin_roles_names(discord_server_id=discord_server_id)
        user = ctx.message.author
        valid = False
        for role in user.roles:
            if role.name in admin_role_names:
                valid = True
                break
        if valid:
            func(self, *args, **kwargs)
    return check
