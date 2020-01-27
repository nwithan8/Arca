from .emby import Emby


def setup(bot):
    bot.add_cog(Emby(bot))
