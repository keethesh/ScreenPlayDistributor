import json
import os
import re

import aiofiles
import discord
from discord.ext.commands import Bot
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("DISCORD_TOKEN")
client = Bot(command_prefix="$key ", case_insensitive=True)
keys_file = "keys.json"


@client.event
async def on_ready():
    print("Bot started!")


async def get_keys(keys_json: str):
    async with aiofiles.open(keys_json) as f:
        keys = json.loads(await f.read())
    return keys


async def update_keys(keys_json: str, keys: dict):
    jsonified_dict = json.dumps(keys, indent=2, sort_keys=True)
    async with aiofiles.open(keys_json, "w+") as f:
        await f.write(jsonified_dict)


async def get_available_key(keys: dict, author_id):
    for key in keys:
        claimed_by = key["claimed_by"]
        steam_key = key["steam_key"]
        if claimed_by == "":
            key["claimed_by"] = str(author_id)
            await update_keys(keys_file, keys)
            return steam_key
    return None


@client.command(help="Sends you a key for ScreenPlay")
async def give(ctx):
    if ctx.author.bot is True:
        return
    author_id = ctx.author.id
    keys = await get_keys(keys_file)
    if any(key["claimed_by"] == str(author_id) for key in keys):
        embed = discord.Embed(title="You have already been given a key. No more keys for you!",
                              color=0x1a58a6)
        await ctx.send(f"{ctx.author.mention}", embed=embed)
        return

    steam_key = await get_available_key(keys, author_id)
    if steam_key is None:
        embed = discord.Embed(title="Unfortunately, there aren't any available keys for the moment. "
                                    "More keys will be added shortly. The admins have been notified.",
                              color=0x1a58a6)
        await ctx.send(embed=embed)
        admin = client.get_user(189271942564544512)
        await admin.send(f"Hey {admin}! There aren't any keys available, any way you could add some?")
        return

    user = client.get_user(author_id)
    embed = discord.Embed(title=f"Check your DMs!",
                          color=0x1a58a6)
    await ctx.send(f"{ctx.author.mention}!", embed=embed)
    await user.send(f"Hey there {user.name}! Here's your ScreenPlay Steam key: `{steam_key}`")


@client.command(help="Reports how much keys are left")
async def count(ctx):
    keys = await get_keys(keys_file)
    total_keys = len(keys)
    available_keys = 0
    for key in keys:
        if key["claimed_by"] == "":
            available_keys += 1
    percentage = (total_keys // available_keys) * 100
    embed = discord.Embed(title=f"{available_keys} keys left out of {total_keys}!\n"
                                f"{percentage}% of keys remaining",
                          color=0x1a58a6)
    await ctx.send(embed=embed)


@client.command(hidden=True)
async def add(ctx, key_to_add):
    if ctx.channel.type is not discord.ChannelType.private:
        return
    elif not re.match("((?![^0-9]{12,}|[^A-z]{12,})([A-z0-9]{4,5}-?[A-z0-9]{4,5}-?[A-z0-9]{4,5}(-?[A-z0-9]"
                      "{4,5}(-?[A-z0-9]{4,5})?)?))", key_to_add):
        await ctx.send(f"`{key_to_add}` is not a valid Steam key")
        return
    keys = await get_keys(keys_file)
    for key in keys:
        if key["steam_key"] == key_to_add:
            await ctx.send(f"`{key_to_add}` is already in the database!")
            return
    keys.append({"steam_key": key_to_add, "claimed_by": ""})
    await update_keys(keys_file, keys)


client.run(token)
