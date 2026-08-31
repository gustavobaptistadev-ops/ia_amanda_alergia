import httpx
import asyncio

async def test():
    res = await httpx.AsyncClient().post('https://api-wpp.ghosthub.com.br/webhook/set', headers={'apikey': 'abc123456'}, json={'url': 'https://tranquil-encouragement-production-52cf.up.railway.app/api/v1/webhook/evolution', 'webhook_by_events': False, 'events': ['MESSAGE']})
    print(res.status_code, res.text)

asyncio.run(test())
