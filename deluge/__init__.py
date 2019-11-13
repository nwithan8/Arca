from .deluge import Deluge

def setup(bot):
	bot.add_cog(Deluge(bot))
