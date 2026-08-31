import httpx
import asyncio

async def test():
    res = await httpx.AsyncClient().post('https://api-wpp.ghosthub.com.br/instance/create', headers={'apikey': '1dcd4e3bc54541449f52c5e319d7eeda'}, json={'instanceName': 'ia_amanda_api'})
    print(res.status_code, res.text)

asyncio.run(test())
