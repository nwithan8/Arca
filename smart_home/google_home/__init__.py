from .google_home import GoogleHome

def setup(bot):
	bot.add_cog(GoogleHome(bot))
