from .recorder import Recorder


async def setup(bot):
    await bot.add_cog(Recorder(bot))
