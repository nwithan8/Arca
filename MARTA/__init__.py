from .martacog import MARTA

def setup(bot):
	bot.add_cog(MARTA(bot))
