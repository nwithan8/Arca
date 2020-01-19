from .plex_manager_nodb import PlexManager


def setup(bot):
    bot.add_cog(PlexManager(bot))
