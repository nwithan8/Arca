import general.vc_gaming_manager as VC
from .speedtest import SpeedTest


def setup(bot):
    VC.setup(bot)
    bot.add_cog(SpeedTest(bot))