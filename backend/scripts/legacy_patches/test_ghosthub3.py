import httpx
import asyncio

async def test():
    res = await httpx.AsyncClient().post('https://api-wpp.ghosthub.com.br/instance/create', headers={'apikey': '1dcd4e3bc54541449f52c5e319d7eeda'}, json={'name': 'ia_amanda_api3', 'token': 'abc123456', 'qrcode': True})
    print(res.status_code, res.text)

asyncio.run(test())
