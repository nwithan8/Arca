import general.vc_gaming_manager as VC
from .speedtest import SpeedTest
from .coronavirus import Coronavirus


def setup(bot):
    VC.setup(bot)
    bot.add_cog(SpeedTest(bot))
    bot.add_cog(Coronavirus(bot))
