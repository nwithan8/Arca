from .jellyfin import Jellyfin

def setup(bot):
	bot.add_cog(Jellyfin(bot))
