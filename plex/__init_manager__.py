from .plex_manager import PlexManager


def setup(bot):
    bot.add_cog(PlexManager(bot))
