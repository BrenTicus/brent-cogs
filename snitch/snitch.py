import asyncio
import discord
import logging
import re
from datetime import timezone
from typing import List, Optional, Union
from redbot.core import checks, Config, commands
from redbot.core.utils.chat_formatting import pagify


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

    @commands.group("snitch")
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def _snitch(self, ctx: commands.Context):
        """Base command to manage snitch settings."""
        pass

    def _identify_target(
        self, ctx: commands.Context, target: str
    ) -> Union[discord.abc.Messageable, None]:
        """Try to convert a potential target into a messageable interface.

        :param ctx: The Discord Red command context.
        :type ctx: commands.Context
        :param target: The potential target.
        :type target: str
        :return: If the target can be mapped, a Messagable. Otherwise None.
        :rtype: Union[discord.abc.Messageable, None]
        """
        coerced = None
        server = ctx.guild
        # We need to figure out what was passed in. If they're passed in as their ID, it's relatively easy, just
        # try to coerce the value into an appropriate object and if it works bail out. As a bonus, these aren't
        # async so we can just fudge it like so.
        maybe_id = target.strip("!<#>@&")
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
        """Add people, roles, or channels to a notification group. IDs can be passed in using # or @ as appropriate.
        Text input will be evaluated checking roles, then members, then channels. @everyone also works.

        Example:
            `[p]snitch to tech #tech-general @Site.Tech Brenticus`

        :param ctx: The Discord Red command context.
        :type ctx: commands.Context
        :param group: The notification group to modify.
        :type group: str
        :param targets: The list of targets to notify.
        :type targets: List[str]
        """
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
            notifygroups[group] = notifygroup

    @_snitch.command(name="notto")
    async def _snitch_del(self, ctx: commands.Context, group: str, *targets: str):
        """Remove people, roles, or channels from a notification group.

        Example:
            `[p]snitch notto tech #tech-general`

        :param ctx: The Discord Red command context.
        :type ctx: commands.Context
        :param group: The notification group to modify.
        :type group: str
        :param targets: The list of targets to notify.
        :type targets: List[str]
        """
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

    @_snitch.command(name="on", require_var_positional=True)
    async def _words_add(self, ctx: commands.Context, group: str, *words: str):
        """Add trigger words to the notification group. Use double quotes to add sentences.

        Example:
            `[p]snitch on tech computer wifi it`

        :param ctx: The Discord Red command context.
        :type ctx: commands.Context
        :param group: The notification group to modify.
        :type group: str
        :param words: The list of trigger words to notify on.
        :type words: List[str]
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
    async def _words_remove(self, ctx: commands.Context, group: str, *words: List[str]):
        """Remove trigger words from the notification group. Use double quotes to remove sentences.

        Examples:
            - `[p]snitch noton text wifi`

        :param ctx: The Discord Red command context.
        :type ctx: commands.Context
        :param group: The notification group to modify.
        :type group: str
        :param words: The list of trigger words to notify on.
        :type group: List[str]
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

    @_snitch.command(name="with", require_var_positional=True)
    async def _message_change(self, ctx: commands.Context, group: str, message: str):
        """Change the message sent with your snitch.

        Tokens:
            {{author}} - The display name of the message author.
            {{channel}} - The channel name the message originated in.
            {{server}} - The server name the message originated in.
            {{words}} - The list of words that triggered the message.

        :param ctx: The Discord Red command context.
        :type ctx: commands.Context
        :param group: The notification group to modify.
        :type group: str
        :param message: The message to send with any notifications for this group.
        :type message: str
        """
        server = ctx.guild
        async with self.config.guild(server).notifygroups() as notifygroups:
            notifygroup = notifygroups.get(group)
            if not notifygroup:
                notifygroup = {"words": [], "targets": {}}
            notifygroup["message"] = message
            notifygroups[group] = notifygroup
            await ctx.channel.send(f"Message for {group} updated.")

    @_snitch.command(name="clear")
    async def _clear_list(self, ctx: commands.Context):
        """Wipe out all config data.

        Example:
            [p]snitch clear

        :param ctx: The Discord Red command context.
        :type ctx: commands.Context
        """
        await self.config.guild(ctx.guild).notifygroups.clear()
        await ctx.channel.send("Cleared all snitch settings.")

    @_snitch.command(name="list")
    async def _global_list(self, ctx: commands.Context):
        """Send a list of this server's people and words involved in snitching.

        Example:
            [p]snitch list

        :param ctx: The Discord Red command context.
        :type ctx: commands.Context
        """
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
            logging.error(
                f"EXCEPTION {e}\n  Can't send message to channel.\n  Triggered on {ctx.message.clean_content} by {author}"
            )
            await ctx.send("I can't send direct messages to you.")

    async def _send_to_member(
        self,
        member: discord.Member,
        message: str,
        embed: Optional[discord.Embed] = None,
    ):
        """DM a member.

        Note that there are a lot of failure cases here based on permissions of the bot and privacy settings of server
        members. These get logged in case the bot owner needs to investigate.

        :param member: The member who the bot will DM.
        :type member: discord.Member
        :param message: The message to send.
        :type message: str
        :param embed: The embed to include with the message.
        :type embed: discord.Embed
        """
        try:
            if member.bot:
                return
            await member.send(content=message, embed=embed)
            logging.info(f"Sent {message} to {member.display_name}.")
        except Exception as e:
            logging.error(
                f'EXCEPTION {e}\n  Failed in sending "{message}" to {member.display_name}.'
            )

    async def _notify_words(
        self,
        message: discord.Message,
        targets: list,
        words: list,
        base_msg: Optional[str] = None,
    ):
        """Notify the targets configured to be notifies.

        :param message: The message that triggered this notification.
        :type message: discord.Message
        :param targets: The list of targets to be notified.
        :type targets: list
        :param words: The list of words that triggered this notification.
        :type words: list
        :param base_msg: The base message to send with the notification. See _message_change() for more info.
        :type base_msg: Optional[str]
        """
        word_msg = " and ".join(words)
        base_msg = base_msg or "Snitching on {{author}} for saying {{words}}"
        base_msg = (
            base_msg.replace("{{author}}", message.author.display_name)
            .replace("{{words}}", word_msg)
            .replace("{{server}}", message.guild.name)
            .replace("{{channel}}", message.channel.name)
        )

        embed = discord.Embed(
            title=f"{message.author.display_name} in {message.channel}",
            type="link",
            description=message.content,
            url=message.jump_url,
            colour=discord.Color.red(),
        ).set_thumbnail(url=message.author.avatar_url)
        # Loop over all the targets identified in the config and send them a message.
        waitlist = []
        for target in targets:
            try:
                target_id = target["id"]
                target_type = target["type"]
                if target_type == "TextChannel":
                    chan = message.guild.get_channel(target_id)
                    waitlist.append(chan.send(f"@everyone {base_msg}", embed=embed))
                    logging.info(f"Sent {message} to {chan.name}.")
                elif target_type == "Member":
                    member = message.guild.get_member(target_id)
                    waitlist.append(self._send_to_member(member, base_msg, embed))
                elif target_type == "Role":
                    role = message.guild.get_role(target_id)
                    for member in role.members:
                        waitlist.append(self._send_to_member(member, base_msg, embed))
            except Exception as e:
                logging.error(
                    f"EXCEPTION {e}\n  Trying to message {target}\n  Triggered on {message.clean_content} by {message.author}"
                )
        # We only await at the end since an @everyone in a big server takes freaking forever otherwise.
        if waitlist:
            await asyncio.wait(waitlist, return_when=asyncio.ALL_COMPLETED)

    async def _check_words(self, message: discord.Message):
        """Check whether we really should notify people.

        :param message: The message to check for trigger words.
        :type message: discord.Message
        """
        server = message.guild

        async with self.config.guild(server).notifygroups() as notifygroups:
            for notifygroup in notifygroups.values():
                word_list = notifygroup.get("words")
                # Escape and combine the words into a regex matching string.
                if word_list:
                    pattern = re.compile(
                        "|".join(rf"\b{re.escape(w)}\b" for w in word_list), flags=re.I
                    )
                else:
                    pattern = None
                matches = None
                if pattern:
                    # See if there are any hits.
                    matches = set(pattern.findall(message.content))
                if matches:
                    # If there are, tell the targets.
                    await self._notify_words(
                        message,
                        notifygroup["targets"].values(),
                        matches,
                        base_msg=notifygroup.get("message"),
                    )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Check every message the bot can see for trigger words.

        :param message: The message.
        :type message: discord.Message
        """
        # This can only run in servers.
        if message.guild is None:
            return
        # Make sure the bot is allowed in the server.
        if await self.bot.cog_disabled_in_guild(self, message.guild):
            return
        # Check if the message starts with a prefix, indicating it's a command.
        prefixes = await self.bot.get_prefix(message)
        prefix_check = (
            isinstance(prefixes, str) and message.clean_content.startswith(prefixes)
        ) or (
            isinstance(prefixes, list)
            and any([True for y in prefixes if message.clean_content.startswith(y)])
        )
        if prefix_check:
            return
        # Check if the message was sent by an actual person.
        author = message.author
        valid_user = isinstance(author, discord.Member) and not author.bot
        if not valid_user:
            return
        # Check if automod contexts would normally ignore this message.
        if await self.bot.is_automod_immune(message):
            return
        # Now we shuffle the work off to another method.
        await self._check_words(message)

    @commands.Cog.listener()
    async def on_message_edit(self, _prior, message: discord.Message):
        """Check every edit the bot can see for trigger words.

        :param _prior: The message prior to editing.
        :type _prior: None
        :param message: The message post edit.
        :type message: dicord.Message
        """
        await self.on_message(message)
