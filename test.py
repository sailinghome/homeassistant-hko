import asyncio
import aiohttp
from hko import HKO

async def main():
    async with aiohttp.ClientSession() as session:
        hko = HKO(session)
        data = await hko.async_get_rhrread()
        temp = (next((item.value for item in data.temperature if item.place == "Tai Po"), 0))
        print(temp)

asyncio.run(main())