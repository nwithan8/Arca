from .espn_scores import ESPNScores

def setup(bot):
	bot.add_cog(ESPNScores(bot))
