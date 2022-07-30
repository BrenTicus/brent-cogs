from .recorder import Recorder


def setup(bot):
    bot.add_cog(Recorder(bot))
