import httpx
import asyncio

async def test():
    res = await httpx.AsyncClient().get('https://api-wpp.ghosthub.com.br/instance/fetchInstances', headers={'apikey': '1dcd4e3bc54541449f52c5e319d7eeda'})
    print(res.status_code, res.text)

asyncio.run(test())
