import asyncio
import logging
import psutil
import aiohttp
import discord
from typing import Union
from discord.ext import commands


class DisstatError(Exception):
    def __init__(self, message: str, status_code: int):
        self.status_code = status_code
        if status_code == 401:
            message = "Invalid API key"
        super().__init__(message + " " + str(status_code))


class Disstat:
    base_url = f"https://disstat-api.tomatenkuchen.com"
    task = None
    custom_queue = []

    def __init__(self, bot: Union[discord.Client, discord.AutoShardedClient], key: str):
        """
        Initializes the class instance.

        Args:
            bot (Union[discord.Client, discord.AutoShardedClient]): The bot instance.
            key (str): The key for the API.

        Returns:
            None
        """
        self.bot = bot
        self.key = key
        self.is_sharded = isinstance(bot, discord.AutoShardedClient)
        self.previous_bandwidth: int = psutil.net_io_counters().bytes_sent + psutil.net_io_counters().bytes_recv

    async def get_bot_info(self, bot_id: Union[int, str] = None):
        """
        Retrieves information about a bot using the bot ID.
        Args:
            bot_id (Union[int, str], optional): The ID of the bot to retrieve information for. If not provided, the ID of the bot associated with the instance will be used. Defaults to None.
        Returns:
            dict: A dictionary containing the bot information.
        Raises:
            DisstatError: If retrieving bot information fails.
        """
        async with aiohttp.ClientSession(base_url=self.base_url) as s:
            async with s.get(f"/v1/bot/{bot_id or self.bot.user.id}", headers={"Authorization": self.key}) as r:
                if r.status != 200:
                    raise DisstatError(f"Disstat getting bot info failed", r.status)
                return await r.json()

    async def post_command_raw(self, command_name: str, user_id: int = 0, guild_id: int = 0):
        """
        This function posts a raw command to the API.
        Args:
            command_name (str): The name of the command.
            user_id (int, optional): The ID of the user. Defaults to 0.
            guild_id (int, optional): The ID of the guild. Defaults to 0.
        Raises:
            ValueError: If the command_name is empty.
            DisstatError: If the request to post custom data fails.
        Returns:
            None
        """
        if not command_name.strip():
            raise ValueError("command_name cannot be empty")
        await self.post_custom("command", command_name, user_id, guild_id)

    async def post_command(self, ctx: Union[discord.Interaction, commands.Context]):
        """
        Post a command to the server.

        Args:
            ctx (Union[discord.Interaction, commands.Context]): The context of the command.

        Raises:
            ValueError: If ctx is not an Interaction or Context.
            ValueError: If ctx is a Command Interaction without a command.
            DisstatError: If the request to post custom data fails.
        Returns:
            None
        """
        if not isinstance(ctx, (discord.Interaction, commands.Context)):
            raise ValueError("ctx must be an Interaction or Context")
        if isinstance(ctx, discord.Interaction):
            if ctx.command is None and ctx.type == discord.InteractionType.application_command:
                raise ValueError("ctx must be an Command Interaction")
        command_name = ctx.command.name
        guild_id = ctx.guild.id if ctx.guild is not None else 0
        user_id = ctx.author.id if isinstance(ctx, commands.Context) else ctx.user.id
        await self.post_command_raw(command_name, user_id, guild_id)

    async def post_custom(self, graph_type: str, value1: Union[int, str] = 0, value2: Union[int, str] = 0,
                          value3: Union[int, str] = 0):
        """
        This function posts custom data to the API.
        Args:
            graph_type (str): The type of graph to post the custom data to.
            value1 (int, optional): The first value to post. Defaults to 0.
            value2 (int, optional): The second value to post. Defaults to 0.
            value3 (int, optional): The third value to post. Defaults to 0.
        Raises:
            ValueError: If the graph_type is empty.
            DisstatError: If the request to post custom data fails.
        Returns:
            None
        """
        if not graph_type.strip():
            raise ValueError("graph_type cannot be empty")
        data = {
            "type": graph_type,
            "value1": value1,
            "value2": value2,
            "value3": value3
        }
        if self.task is not None:
            self.custom_queue.append(data)
            return
        async with aiohttp.ClientSession(base_url=self.base_url) as s:
            async with s.post(f"/v1/bot/{self.bot.user.id}/custom", json=data, headers={"Authorization": self.key}) as r:
                if r.status != 200:
                    raise DisstatError(f"Disstat posting custom failed", r.status)

    async def post_stat(self, data: dict = None):
        """
        Posts statistics to the API.

        Args:
            data (dict): The data to be posted. Default is None.

        Raises:
            ValueError: If the data dictionary is empty.
            TypeError: If the data is not of type dict.
            Exception: If the API call fails.

        Returns:
            None
        """
        await self.bot.wait_until_ready()
        data_post = {}
        if data is None:
            if self.is_sharded:
                data_post["shards"] = self.bot.shard_count

            current_bandwidth = psutil.net_io_counters().bytes_sent + psutil.net_io_counters().bytes_recv
            data_post["bandwidth"] = current_bandwidth - self.previous_bandwidth
            self.previous_bandwidth = current_bandwidth

            data_post["cpu"] = int(psutil.cpu_percent())

            data_post["ramUsage"] = psutil.virtual_memory().used

            data_post["ramTotal"] = psutil.virtual_memory().total

            data_post["apiPing"] = int(self.bot.latency * 1000)

            data_post["users"] = len(self.bot.users)

            data_post["guilds"] = len(self.bot.guilds)

            if self.custom_queue:
                data_post["custom"] = self.custom_queue
                self.custom_queue = []
        else:
            data_post = data

        if not data_post:
            raise ValueError("dict must not be empty")
        elif not type(data_post) is dict:
            raise TypeError("must be of dict")

        async with aiohttp.ClientSession(base_url=self.base_url) as s:
            async with s.post(f"/v1/bot/{self.bot.user.id}", json=data_post, headers={"Authorization": self.key}) as r:
                if r.status != 204:
                    raise DisstatError(f"Disstat posting stat failed", r.status)

    async def __loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                await self.post_stat()
            except Exception as e:
                print(e)
            await asyncio.sleep(60)

    def start_loop(self) -> None:
        """
        Starts the loop.

        This function checks if looping is already running. If it is not, it creates a new loop.

        Returns:
            None
        """
        if self.task is None:
            self.task = self.bot.loop.create_task(self.__loop())

    def stop_loop(self) -> None:
        """
        Stop the loop if it is currently running.

        This method checks if the loop has start and stop it.

        Returns:
            None
        """
        if self.task is not None:
            self.task.cancel()
            self.task = None
        else:
            logging.warning("Disstat loop is not running")
