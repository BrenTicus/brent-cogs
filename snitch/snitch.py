import asyncio
import discord
import logging
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
    Cog to notify groups of users, roles, or channels when certain phrases are said.
    Modified from the default Filter module here: https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/cogs/words/words.py
    """

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=586925412)
        default_guild_settings = {"notifygroups": {}}
        self.config.register_guild(**default_guild_settings)
        logging.basicConfig(level=logging.DEBUG, filename="snitch.log")

    @commands.group("snitch")
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def _snitch(self, ctx: commands.Context):
        """Base command to manage snitch settings."""
        pass

    def _identify_target(self, ctx: commands.Context, target):
        coerced = None
        server = ctx.guild
        # We need to figure out what was passed in. If they're passed in as their ID, it's relatively easy, just
        # try to coerce the value into an appropriate object and if it works bail out. As a bonus, these aren't
        # async so we can just fudge it like so.
        maybe_id = target.strip("!<#>")
        logging.info(f"ID candidate: {maybe_id}")
        if maybe_id.isnumeric():
            if coerced := server.get_member(int(maybe_id)):
                pass
            elif coerced := server.get_role(int(maybe_id)):
                pass
            elif coerced := server.get_channel(int(maybe_id)):
                pass
        # If that doesn't work we need to filter through a bunch of object names to find a match.
        elif not coerced:
            # Check roles for matches.
            matches = [
                role for role in ctx.guild.roles if role.name.lower() == target.lower()
            ]
            # Grab the first match if one exists.
            coerced = matches.pop(0) if any(matches) else None
            # If no match do the same for members.
            if not coerced:
                matches = [
                    member
                    for member in ctx.guild.members
                    if member.name.lower() == target.lower()
                    or member.display_name.lower() == target.lower()
                ]
                coerced = matches.pop(0) if any(matches) else None
            # And channels.
            if not coerced:
                matches = [
                    channel
                    for channel in ctx.guild.channels
                    if channel.name.lower() == target.lower()
                    and isinstance(channel, discord.TextChannel)
                ]
                coerced = matches.pop(0) if any(matches) else None
        return coerced

    @_snitch.command(name="to")
    async def _snitch_add(self, ctx: commands.Context, group: str, *targets: str):
        """Add people, roles, or channels to a notification group.
        IDs can be passed in using # or @ as appropriate. Text input will be evaluated checking roles, then members,
        then channels.
        Example:
            `[p]snitch to tech #tech-general @Site.Tech Brenticus`"""
        server = ctx.guild
        async with self.config.guild(server).notifygroups() as notifygroups:
            notifygroup = notifygroups.get(group)
            if not notifygroup:
                notifygroup = {"words": [], "targets": {}}
            for target in targets:
                coerced = self._identify_target(ctx, target)
                # We store the coerced value so things are easier later.
                if coerced:
                    target_type = type(coerced).__name__
                    notifygroup["targets"][target] = {
                        "id": coerced.id,
                        "type": target_type,
                    }
                    await ctx.channel.send(f"{target_type} {target} will be notified.")
                else:
                    await ctx.channel.send(f"Could not identify {target}.")
                    joined = ", ".join(notifygroup["targets"])
                    await ctx.channel.send(
                        f"Couldn't find {target} in {group}. Options: {joined}"
                    )
                    logging.warning(
                        f"Couldn't find {target} in {group}. Options: {joined}"
                    )
            notifygroups[group] = notifygroup

    @_snitch.command(name="notto")
    async def _snitch_del(self, ctx: commands.Context, group: str, *targets: str):
        """Remove people, roles, or channels from a notification group.
        Example:
            `[p]snitch notto tech #tech-general`"""
        server = ctx.guild
        async with self.config.guild(server).notifygroups() as notifygroups:
            notifygroup = notifygroups.get(group)
            if not notifygroup:
                await ctx.channel.send(f"Group doesn't exist.")
            for target in targets:
                if target in notifygroup["targets"]:
                    notifygroup["targets"].pop(target)
                    await ctx.channel.send(f"Removed {target}.")
                else:
                    await ctx.channel.send(f"Couldn't find {target}.")
                    joined = ", ".join(notifygroup["targets"])
                    await ctx.channel.send(
                        f"Couldn't find {target} in {group}. Options: {joined}"
                    )
                    logging.warning(
                        f"Couldn't find {target} in {group}. Options: {joined}"
                    )

    @_snitch.command(name="on", require_var_positional=True)
    async def _words_add(self, ctx: commands.Context, group: str, *words: str):
        """Add words to the filter.
        Use double quotes to add sentences.
        Examples:
            `[p]snitch on tech computer wifi it`
        **Arguments:**
        - `[words...]` The words or sentences to filter.
        """
        server = ctx.guild
        async with self.config.guild(server).notifygroups() as notifygroups:
            notifygroup = notifygroups.get(group)
            if not notifygroup:
                notifygroup = {"words": [], "targets": {}}
            for word in words:
                if not word in notifygroup["words"]:
                    notifygroup["words"].append(word)
                await ctx.channel.send(f"{word} will trigger a notification.")
            notifygroups[group] = notifygroup

    @_snitch.command(name="noton", require_var_positional=True)
    async def _words_remove(self, ctx: commands.Context, group: str, *words: str):
        """Remove words from the filter.
        Use double quotes to remove sentences.
        Examples:
            - `[p]snitch noton text wifi`
        **Arguments:**
        - `[words...]` The words or sentences to no longer filter.
        """
        server = ctx.guild
        async with self.config.guild(server).notifygroups() as notifygroups:
            notifygroup = notifygroups.get(group)
            if not notifygroup:
                notifygroup = {"words": [], "targets": {}}
            for word in words:
                notifygroup["words"].remove(word)
                await ctx.channel.send(f"{word} will no longer trigger a notification.")
            notifygroups[group] = notifygroup

    @_snitch.command(name="clear")
    async def _clear_list(self, ctx):
        """Wipe out all config data."""
        await self.config.guild(ctx.guild).notifygroups.clear()
        await ctx.channel.send("Cleared all snitch settings.")

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
        group_text = "Filtered in this server:" + "\n"
        for name, vals in group_list.items():
            people = ", ".join(vals["targets"].keys())
            words = ", ".join(vals["words"])
            group_text += f"\t{name} tells {people} about {words}\n"
        try:
            for page in pagify(group_text, delims=[" ", "\n"], shorten_by=8):
                await ctx.channel.send(page)
        except Exception as e:
            logging.error(e)
            await ctx.channel.send(e)
            await ctx.send("I can't send direct messages to you.")

    async def _send_to_member(
        self,
        member: discord.Member,
        message: str,
        embed: discord.Embed,
    ):
        if member.bot:
            return
        await member.send(content=message, embed=embed)
        logging.info(f"Sent {message} to {member.display_name}.")

    async def _notify_words(self, message: discord.Message, targets: list, words: list):
        """Notify people who need to be notified."""
        word_msg = " and ".join(words)
        base_msg = f"Snitching on {message.author.display_name} for saying {word_msg}"
        embed = discord.Embed(
            title=f"{message.author.display_name} in {message.channel}",
            type="link",
            description=message.content,
            url=message.jump_url,
            colour=discord.Color.red(),
        )
        for target in targets:
            try:
                target_id = target["id"]
                target_type = target["type"]
                if target_type == "TextChannel":
                    chan = message.guild.get_channel(target_id)
                    await chan.send(f"@everyone {base_msg}", embed=embed)
                elif target_type == "Member":
                    member = message.guild.get_member(target_id)
                    await self._send_to_member(member, base_msg, embed)
                elif target_type == "Role":
                    role = message.guild.get_role(target_id)
                    for member in role.members:
                        await self._send_to_member(member, base_msg, embed)
            except Exception as e:
                await ctx.channel.send(e)
                logging.error(e)

    async def _check_words(self, message: discord.Message):
        """Check whether we really should notify people."""
        server = message.guild

        async with self.config.guild(server).notifygroups() as notifygroups:
            for notifygroup in notifygroups.values():
                word_list = notifygroup["words"]
                if word_list:
                    pattern = re.compile(
                        "|".join(rf"\b{re.escape(w)}\b" for w in word_list), flags=re.I
                    )
                else:
                    pattern = None
                matches = None
                if pattern:
                    matches = set(pattern.findall(message.content))
                if matches:
                    await self._notify_words(
                        message, notifygroup["targets"].values(), matches
                    )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None:
            return

        if await self.bot.cog_disabled_in_guild(self, message.guild):
            return

        prefixes = await self.bot.get_prefix()
        prefix_check = (
            lambda x: x is str
            and message.clean_content.startswith(x)
            or x is list
            and any([y for y in x if message.clean_content.startswith(y)])
        )
        await message.channel.send(f"Prefixes: {prefixes}")
        if prefix_check(prefixes):
            return

        author = message.author
        valid_user = isinstance(author, discord.Member) and not author.bot
        if not valid_user:
            return

        if await self.bot.is_automod_immune(message):
            return

        await self._check_words(message)

    @commands.Cog.listener()
    async def on_message_edit(self, _prior, message):
        # message content has to change for non-bot's currently.
        # if this changes, we should compare before passing it.
        await self.on_message(message)
