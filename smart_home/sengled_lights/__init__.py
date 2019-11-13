from .sengled import Sengled

def setup(bot):
	bot.add_cog(Sengled(bot))
