import urllib.request
import ssl
import json
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
req = urllib.request.Request(
    'https://iaamandaalergia-production.up.railway.app/api/v1/evolution/fix-webhook',
    method='POST',
    headers={
        'X-API-Key': 'sk_internal_8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e',
        'x-forwarded-proto': 'https',
        'x-forwarded-host': 'iaamandaalergia-production.up.railway.app'
    },
    data=b''
)
try:
    res = urllib.request.urlopen(req, context=ctx)
    print(res.status)
    print(res.read().decode())
except Exception as e:
    print(e)
