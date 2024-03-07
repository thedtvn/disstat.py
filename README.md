# DisStat.py
The unofficial pypi package for [DisStat](https://statcord.com/) -
DisStat itself is [open source](https://github.com/Statcord/DisStat) btw!

You can find the public HTTP api docs on https://statcord.com/docs if you dont want to use an api wrapper.

# Installation
```bash
pip install disstat.py
```

# Main usage

```py
import os
import discord
from discord.ext import commands
from disstat import Disstat

intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)
# initialize DisStat
bot.disstat = Disstat(bot, "YOUR_DISSTAT_TOKEN_HERE")

@bot.event
async def setup_hook():
    # start the background task to post statistics
    bot.disstat.start_loop()

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

@bot.event
async def on_command(ctx: commands.Context):
    # log command has been used
    await bot.disstat.post_command(ctx)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    # log slash command has been used
    if interaction.type is not discord.InteractionType.application_command:
        return 
    await bot.disstat.post_command(interaction)

@bot.event
async def on_message(message: discord.Message):
    # your command logic ...
    
    await bot.disstat.post_command_raw(command_name, user_id, guild_id)
    # this function posts a raw command to the API

@bot.command()
async def stop_bg(ctx: commands.Context):
    # stop the background task
    bot.disstat.stop_loop()
    await ctx.send("done")
    
@bot.command()
async def ping(ctx: commands.Context):
    await ctx.send("pong")

@bot.tree.command(name="ping")
async def s_ping(interaction: discord.Interaction):
    await interaction.response.send_message("pong")


bot.run('YOUR_TOKEN_HERE')

```
