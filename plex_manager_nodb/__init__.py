from .plex_nodb import PlexManager

def setup(bot):
	bot.add_cog(PlexManager(bot))
