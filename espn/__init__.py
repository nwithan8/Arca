from .espn import ESPN

def setup(bot):
	bot.add_cog(ESPN(bot))
