from .news import News

def setup(bot):
	bot.add_cog(News(bot))
