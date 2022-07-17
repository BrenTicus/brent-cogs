import asyncio
import discord
import re
from datetime import timezone
from typing import Union, Set, Literal, Optional

from redbot.core import checks, Config, modlog, commands
from redbot.core.bot import Red
from redbot.core.utils.predicates import MessagePredicate
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import pagify, humanize_list


class Snitch(commands.Cog):
    """
    Cog to notify certain users or roles when certain phrases are said.
    Most of this is modified from the default Filter module here: https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/cogs/words/words.py
    """

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=586925412)
        default_guild_settings = {"notifygroups": {}}
        self.config.register_guild(**default_guild_settings)

    @commands.group("snitch")
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def _snitch(self, ctx: commands.Context):
        """Base command to manage snitch settings."""
        pass

    def _valid_channel(ctx: commands.Context, channel: str) -> bool:
        channel_list = ctx.guild.channels
        for chan in channel_list:
            if chan.name == channel:
                return True
        return False

    @_snitch.command(name="to")
    async def _snitch_add(self, ctx: commands.Context, group: str, *targets: str):
        """Add people, roles, or channels to a notification group.
        Example:
            `[p]snitch to tech #tech-general @Site.Tech`"""
        server = ctx.guild
        async with self.config.guild(server).notifygroups() as notifygroups:
            notifygroup = notifygroups.get(group)
            if not notifygroup:
                notifygroup = {"words": [], "targets": []}
            for target in targets:
                # TODO: handle channels
                notifygroup["targets"].append(target)
                await ctx.channel.send(f"{target} will be notified.")
            notifygroups[group] = notifygroup

    @_snitch.command(name="stopto")
    async def _snitch_del(self, ctx: commands.Context, group: str, *targets: str):
        """Remove people, roles, or channels to a notification group.
        Example:
            `[p]snitch stopto tech #tech-general`"""
        pass

    @_snitch.command(name="list")
    async def _global_list(self, ctx: commands.Context):
        """Send a list of this server's people and words involved in snitching.
        Example:
            [p]snitch list"""
        server = ctx.guild
        author = ctx.author
        group_list = await self.config.guild(server).notifygroups()
        if not group_list:
            await ctx.send(
                "There are no current notification groups set up in this server."
            )
            return
        for name, vals in group_list:
            print(vals)
            people = "placeholder"
            words = "another placeholder"
            group_text = f"{name} tells {people} about {words}"
        group_text = _("Filtered in this server:") + "\n\n" + group_text
        group_text = "Filtered in this server:" + "\n"
        for name, vals in group_list.items():
            print(f"{name}: {vals}")
            people = ", ".join(vals["targets"])
            words = ", ".join(vals["words"])
            group_text += f"\t{name} tells {people} about {words}\n"
        try:
            for page in pagify(group_text, delims=[" ", "\n"], shorten_by=8):
                await author.send(page)
                await ctx.channel.send(page)
        except discord.Forbidden:
            await ctx.send(_("I can't send direct messages to you."))
            await ctx.send("I can't send direct messages to you.")

    @_snitch.command(name="on", require_var_positional=True)
    async def words_add(self, ctx: commands.Context, group: str, *words: str):
        """Add words to the filter.
        Use double quotes to add sentences.
        Examples:
            `[p]snitch on tech computer wifi it`
        **Arguments:**
        - `[words...]` The words or sentences to filter.
        """
        server = ctx.guild
        added = False
        async with self.config.guild(server).notifygroups(group).words() as cur_list:
            for w in words:
                if w.lower() not in cur_list and w:
                    cur_list.append(w.lower())
                    added = True
        if added:
            await ctx.send("Words successfully added to filter.")
        else:
            await ctx.send("Those words were already in the filter.")

    @_snitch.command(
        name="noton", aliases=["remove", "del"], require_var_positional=True
    )
    async def words_remove(self, ctx: commands.Context, group: str, *words: str):
        """Remove words from the filter.
        Use double quotes to remove sentences.
        Examples:
            - `[p]filter remove word1 word2 word3`
            - `[p]filter remove "This is a sentence"`
        **Arguments:**
        - `[words...]` The words or sentences to no longer filter.
        """
        server = ctx.guild
        removed = False
        async with self.config.guild(server).notifygroups(group).words() as cur_list:
            for w in words:
                if w.lower() in cur_list:
                    cur_list.remove(w.lower())
                    removed = True
        if removed:
            await ctx.send("Words successfully removed from filter.")
        else:
            await ctx.send("Those words weren't in the filter.")

    async def filter_hits(
        self,
        text: str,
        server: discord.Guild,
    ) -> Set[str]:
        if isinstance(server, discord.Guild):
            guild = server
            channel = None

        hits: Set[str] = set()

        # word_list = set(await self.config.guild(guild).words())
        # TODO: fix above to check all words, remove below
        word_list = ["test", "butt", "jerk"]

        if word_list:
            pattern = re.compile(
                "|".join(rf"\b{re.escape(w)}\b" for w in word_list), flags=re.I
            )
        else:
            pattern = None

        if pattern:
            hits |= set(pattern.findall(text))
        return hits

    async def check_words(self, message: discord.Message):
        guild = message.guild
        channel = message.channel
        author = message.author
        guild_data = await self.config.guild(guild).all()
        member_data = await self.config.member(author).all()
        created_at = message.created_at

        hits = await self.filter_hits(message.content, message.channel)

        if hits:
            try:
                # TODO: notify in the right spots
                words = "".join(hits)
                await channel.send(f"{author} said these words in {channel}: {words}")
                pass
            except discord.HTTPException:
                pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None:
            return

        if await self.bot.cog_disabled_in_guild(self, message.guild):
            return

        author = message.author
        valid_user = isinstance(author, discord.Member) and not author.bot
        if not valid_user:
            return

        if await self.bot.is_automod_immune(message):
            return

        await self.check_words(message)

    @commands.Cog.listener()
    async def on_message_edit(self, _prior, message):
        # message content has to change for non-bot's currently.
        # if this changes, we should compare before passing it.
        await self.on_message(message)
