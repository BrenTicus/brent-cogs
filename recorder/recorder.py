import asyncio
import discord
import logging
import pathlib
from redbot.core import checks, Config, commands
from redbot.core.data_manager import cog_data_path


class Recorder(commands.Cog):
    """
    Cog to record every message in the server to log files.
    """

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, identifier=675274376)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message, *, edit=False):
        """Check and record every message the bot sees.

        :param message: The message.
        :type message: discord.Message
        """
        # This can only run in servers.
        if message.guild is None:
            return
        # Make sure the bot is allowed in the server.
        if await self.bot.cog_disabled_in_guild(self, message.guild):
            return
        # Collect some information
        content = message.clean_content
        if edit:
            content = f"*edit* {content}"
        author = f"{message.author.display_name}/{message.author.name}#{message.author.discriminator}"
        channel = f"{message.channel.name}"
        server = message.guild.name
        time = message.created_at
        # Compile the message and filename.
        log_message = f"{time} | #{channel} | @{author} :: {content}\n"
        log_file = f"recorder.{server}.{channel}.log"
        # Write out the message.
        folder = cog_data_path(cog_instance=self)
        full_path = folder / log_file
        with open(full_path, "a") as file:
            file.write(log_message)
        logging.info(log_message)

    @commands.Cog.listener()
    async def on_message_edit(self, _prior, message: discord.Message):
        """Check every edit the bot can see for trigger words.

        :param _prior: The message prior to editing.
        :type _prior: None
        :param message: The message post edit.
        :type message: dicord.Message
        """
        await self.on_message(message, edit=True)
