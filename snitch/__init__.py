from .snitch import Snitch

def setup(bot):
    bot.add_cog(Snitch(bot))
