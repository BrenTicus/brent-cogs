import asyncio
import discord
import pathlib
from redbot.core import checks, Config, commands, app_commands
from redbot.core.data_manager import cog_data_path


class Nuke(commands.Cog):
    """
    Cog to remove users from a server en masse.
    """

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=235841895)

    async def _remove_users(*users):
        """Actually kick the users from the guild."""
        waitlist = []
        for user in users:
            waitlist.append(asyncio.create_task(user.kick()))

        await asyncio.wait(waitlist, return_when=asyncio.ALL_COMPLETED)

    @commands.command("nuke")
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def nuke(self, ctx: commands.Context, *names):
        """Remove users from the guild matching the group names."""
        if len(names) == 0:
            pass
        pass

    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def nuke_not(self, ctx: commands.Context, *names):
        """Removes users from the guild except those matching the group names."""
        all_roles = await fetch_roles()
        guild = ctx.guild
        exclude_people = []
        # Go over the provided roles and
        for name in names:
            role_filter = [x for x in all_roles if x.name == name]
            if role_filter:
                role = role_filter[0]
                exclude_people = exclude_people + role.members
            else:
                misses.append(name)
        if misses:
            miss_text = ", ".join(misses)
            await ctx.channel.send(
                f"The following roles could not be found: {misses}.\nNot running until all roles are recognized."
            )
            return
        all_members = ctx.guild.members
        kickable_members = [x for x in all_members if x not in exclude_people]
        await _remove_users(kickable_members)
