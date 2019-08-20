from .plex import Plex

def setup(bot):
	bot.add_cog(Plex(bot))
