from .plex_db import PlexManager

def setup(bot):
	bot.add_cog(PlexManager(bot))
