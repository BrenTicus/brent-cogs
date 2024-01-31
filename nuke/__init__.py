from .nuke import Nuke


def setup(bot):
    bot.add_cog(Nuke(bot))
