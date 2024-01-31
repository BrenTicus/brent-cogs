from .nuke import Nuke


async def setup(bot):
    await bot.add_cog(Nuke(bot))
