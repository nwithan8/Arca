import discord
from discord.ext import commands, tasks
import asyncio
import re
from asyncio import ensure_future, gather, get_event_loop, sleep
from collections import deque
from statistics import mean
from time import time

from aiohttp import ClientSession

MIN_DURATION = 7
MAX_DURATION = 30
STABILITY_DELTA = 2
MIN_STABLE_MEASUREMENTS = 6

total = 0
done = 0
sessions = []

""" Speedtest.net """

# Coming soon

""" Fast.com """


async def run(msg):
    token = await get_token()
    urls = await get_urls(token)
    conns = await warmup(urls)
    future = ensure_future(measure(conns))
    result = await progress(future, msg)
    await cleanup()
    return result


async def get_token():
    async with ClientSession() as s:
        resp = await s.get('https://fast.com/')
        text = await resp.text()
        script = re.search(r'<script src="(.*?)">', text).group(1)

        resp = await s.get(f'https://fast.com{script}')
        text = await resp.text()
        token = re.search(r'token:"(.*?)"', text).group(1)
    return token


async def get_urls(token):
    async with ClientSession() as s:
        params = {'https': 'true', 'token': token, 'urlCount': 5}
        resp = await s.get('https://api.fast.com/netflix/speedtest', params=params)
        data = await resp.json()
    return [x['url'] for x in data]


async def warmup(urls):
    conns = [get_connection(url) for url in urls]
    return await gather(*conns)


async def get_connection(url):
    s = ClientSession()
    sessions.append(s)
    conn = await s.get(url)
    return conn


async def measure(conns):
    workers = [measure_speed(conn) for conn in conns]
    await gather(*workers)


async def measure_speed(conn):
    global total, done
    chunk_size = 64 * 2 ** 10
    async for chunk in conn.content.iter_chunked(chunk_size):
        total += len(chunk)
    done += 1


def stabilized(deltas, elapsed):
    return (
            elapsed > MIN_DURATION and
            len(deltas) > MIN_STABLE_MEASUREMENTS and
            max(deltas) < STABILITY_DELTA
    )


async def progress(future, msg):
    start = time()
    measurements = deque(maxlen=10)
    deltas = deque(maxlen=10)

    while True:
        # await sleep(0.1)
        elapsed = time() - start
        speed = total / elapsed / 2 ** 17
        measurements.append(speed)

        embed = discord.Embed(title="Fast.com Test", description=f'⭕ {speed:.3f} Mbps')
        await msg.edit(content="", embed=embed)

        if len(measurements) == 10:
            delta = abs(speed - mean(measurements)) / speed * 100
            deltas.append(delta)

        if done or elapsed > MAX_DURATION or stabilized(deltas, elapsed):
            future.cancel()
            return speed


async def cleanup():
    await gather(*[s.close() for s in sessions])


def main():
    loop = get_event_loop()
    return loop.run_until_complete(run())


class SpeedTest(commands.Cog):

    @commands.group(name="speedtest", aliases=["speed"], pass_context=True)
    async def speedtest(self, ctx: commands.Context, server: str = 'fast'):
        """
        Speedtest the bot's server. Indicate 'Fast' or 'Ookla'
        """
        server = server.lower()
        if server == 'fast':
            speed = await ctx.send(content="Testing from Fast.com")
            results = await run(speed)
            embed = discord.Embed(title="Fast.com Test", description=f'✅ {results:.3f} mbps')
            await speed.edit(content="", embed=embed)
        elif server == 'ookla':
            await ctx.send("Ookla is not currently supported.")
        else:
            await ctx.send("Please try again with 'Fast' or 'Ookla'")


def setup(bot):
    bot.add_cog(SpeedTest(bot))
