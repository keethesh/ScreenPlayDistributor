import json
import os
import re
from copy import deepcopy

import aiofiles
import aiohttp
import discord
import validators
from discord.ext import commands
from discord.ext.commands import Bot
from discord.message import Message
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("DISCORD_TOKEN")
client = Bot(command_prefix="$key ", case_insensitive=True)
keys_file = "keys.json"
steam_key_regex = "((?![^0-9]{12,}|[^A-z]{12,})([A-z0-9]{4,5}-?[A-z0-9]{4,5}-?[A-z0-9]{4,5}(-?[A-z0-9]" \
                  "{4,5}(-?[A-z0-9]{4,5})?)?))"


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
        if claimed_by is None:
            key["claimed_by"] = str(author_id)
            await update_keys(keys_file, keys)
            return steam_key
    return None


async def check_for_duplicates(steam_keys: list, new_keys: list):
    added_keys = 0
    modified_steam_keys = deepcopy(steam_keys)
    for new_key in new_keys:
        is_already_added = False
        for steam_key in steam_keys:
            if steam_key["steam_key"] == new_key:
                is_already_added = True
                break
        if not is_already_added:
            modified_steam_keys.append({"steam_key": new_key, "claimed_by": None})
            added_keys += 1
    return added_keys, modified_steam_keys


async def download_keys(download_link):
    async with aiohttp.ClientSession() as session:
        async with session.get(download_link) as response:
            downloaded_keys = (await response.read()).decode()
    keys = [match.group() for match in re.finditer(steam_key_regex, downloaded_keys)]
    return keys


@client.event
async def on_ready():
    print("Bot started!")


@client.event
async def on_message(message: Message):
    author_id = message.author.id
    keys = await get_keys(keys_file)
    if not (message.author.bot is True or
            any(key["claimed_by"] == str(author_id) for key in keys) or
            message.channel.id not in [704958616087822356, 668477530336133131]):

        steam_key = await get_available_key(keys, author_id)
        if steam_key is None:
            embed = discord.Embed(title="Unfortunately, there aren't any available Steam keys for the moment. "
                                        "More Steam keys will be added shortly. The admins have been notified.",
                                  color=0x1a58a6)
            await message.guild.send(embed=embed)
            admin = client.get_user(189271942564544512)
            await admin.send(f"Hey {admin}! There aren't any Steam keys available, any way you could add some?")
            return

        user = client.get_user(author_id)
        embed = discord.Embed(title=f"Check your DMs!",
                              color=0x1a58a6)
        await message.channel.send(f"{message.author.mention}!", embed=embed)
        await user.send(f"Hey there {user.name}! Here's your ScreenPlay Steam key: `{steam_key}`")
    else:
        await client.process_commands(message)


@client.command(help="Reports how much Steam keys are left")
@commands.cooldown(1, 300, commands.BucketType.guild)
async def count(ctx):
    keys = await get_keys(keys_file)
    total_keys = len(keys)
    available_keys = 0
    for key in keys:
        if key["claimed_by"] is None:
            available_keys += 1
    percentage = (total_keys // available_keys) * 100
    embed = discord.Embed(title=f"{available_keys} Steam keys left out of {total_keys}!\n"
                                f"{percentage}% of Steam keys remaining",
                          color=0x1a58a6)
    await ctx.send(embed=embed)


@client.command(hidden=True)
async def add(ctx, value):
    is_key = False
    is_link = False
    if re.match(steam_key_regex, value):
        is_key = True
    elif validators.url(value):
        is_link = True

    if ctx.channel.type is not discord.ChannelType.private:
        return
    elif not (is_link or is_key):
        await ctx.send(f"`{value}` is not a valid Steam key or link")
        return

    keys = await get_keys(keys_file)
    if is_key:
        if (await check_for_duplicates(keys, [value]))[0] == 0:
            await ctx.send(f"`{value}` is already in the database!")
            return
        await ctx.send(f"Successfully added your key to the database!")
    else:
        try:
            downloaded_keys = await download_keys(value)
            total, keys = await check_for_duplicates(keys, downloaded_keys)
            await ctx.send(f"Successfully added a total of {total} keys to the database out of {len(downloaded_keys)}")
        except Exception as e:
            await ctx.send(f"Received exception: '{e}'. Keys not added.")
    await update_keys(keys_file, keys)


client.run(token)
