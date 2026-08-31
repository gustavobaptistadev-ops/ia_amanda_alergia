import httpx
import asyncio

async def test():
    res = await httpx.AsyncClient().get('https://api-wpp.ghosthub.com.br/instance/qr', headers={'apikey': 'abc123456'})
    print(res.status_code, res.text)

asyncio.run(test())
