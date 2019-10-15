from .booksonic import Booksonic

def setup(bot):
	bot.add_cog(Booksonic(bot))
