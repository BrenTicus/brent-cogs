from .snitch import Snitch

async def setup(bot):
    await bot.add_cog(Snitch(bot))
