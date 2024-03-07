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
    base_url = f"https://statcord.com"
    task = None
    custom_queue = []
    commands_count = {}

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

    async def post_command_raw(self, command_name: str):
        """
        This function posts a raw command to the API.
        Args:
            command_name (str): The name of the command.
        Raises:
            ValueError: If the command_name is empty.
            DisstatError: If the request to post custom data fails.
        Returns:
            None
        """
        if not command_name.strip():
            raise ValueError("command_name cannot be empty")
        if command_name not in self.commands_count:
            self.commands_count[command_name] = 1
        else:
            self.commands_count[command_name] += 1

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
        await self.post_command_raw(command_name)
        
        
    async def custom_graph(self, id_name: str, data: dict):
        """
        This function posts custom data to the API.
        Args:
            id_name (str): The type of graph to post the custom data to.
            data (dict): Key-value pairs of data.
        Raises:
            ValueError: If the graph_type is empty.
        Returns:
            None
        """
        if not id_name.strip():
            raise ValueError("id_name cannot be empty")
        data = {
            "id": id_name,
            "data": data
        }
        for k, i in enumerate(self.custom_queue):
            if i["id"] == id_name:
                self.custom_queue[i]["data"].extend(data["data"])
                return
        self.custom_queue.append(data)

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
                data_post["shardCount"] = self.bot.shard_count
                
            
            # current_bandwidth = psutil.net_io_counters().bytes_sent + psutil.net_io_counters().bytes_recv
            # data_post["bandwidth"] = current_bandwidth - self.previous_bandwidth
            # self.previous_bandwidth = current_bandwidth
            
            data_post["cpuUsage"] = int(psutil.cpu_percent())

            data_post["ramUsage"] = psutil.virtual_memory().used

            data_post["totalRam"] = psutil.virtual_memory().total

            data_post["members"] = len(list(self.bot.get_all_members()))
            
            data_post["userCount"] = len(self.bot.users)

            data_post["guildCount"] = len(self.bot.guilds)

            if self.custom_queue:
                data_post["customCharts"] = self.custom_queue
                self.custom_queue = []
                
            if self.commands_count:
                data_post["commands"] = [{"name": k, "count": v} for k, v in self.commands_count.items()]
        else:
            data_post = data

        if not data_post:
            raise ValueError("dict must not be empty")
        elif not type(data_post) is dict:
            raise TypeError("must be of dict")

        async with aiohttp.ClientSession(base_url=self.base_url) as s:
            async with s.post(f"/api/bots/{self.bot.user.id}/stats", json=data_post, headers={"Authorization": self.key}) as r:
                if r.ok:
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
