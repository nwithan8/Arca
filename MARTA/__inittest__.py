from .martacog_test import MARTA

def setup(bot):
	bot.add_cog(MARTA(bot))
