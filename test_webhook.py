import urllib.request
import ssl
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
req = urllib.request.Request(
    'https://iaamandaalergia-production.up.railway.app/api/v1/webhook/evolution?token=webhook-secret-123',
    method='POST',
    headers={'Content-Type': 'application/json'},
    data=b'{"event":"ping"}'
)
try:
    print(urllib.request.urlopen(req, context=ctx).read().decode())
except Exception as e:
    print(e)
