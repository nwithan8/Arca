from functools import wraps

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

def false_if_error(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        """
        Return False if error encountered
        """
        try:
            return func(self, *args, **kwargs)
        except:
            return False
    return wrapper