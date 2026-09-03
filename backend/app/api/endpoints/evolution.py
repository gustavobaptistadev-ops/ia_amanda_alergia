from fastapi import APIRouter
import httpx
import asyncio
import logging
from app.services.evolution_api import EVOLUTION_API_URL, get_headers

logger = logging.getLogger(__name__)
router = APIRouter()

# Endpoints verificados no GhostHub Evolution GO:
# /instance/status        -> 200 ok | 400 client disconnected
# /instance/qr            -> 200+QR aguardando scan | 400 desconectado
# DELETE /instance/logout -> limpa sessao
# POST /instance/reconnect -> nova sessao (gera QR)
# /connectionState, /connect, /qrcode -> 404 nao existem

@router.get('/status')
async def get_instance_status():
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.get(f'{EVOLUTION_API_URL}/instance/status', headers=get_headers())
            if r.status_code == 200:
                return r.json()
            logger.warning(f'Status da instancia: {r.status_code} - {r.text[:80]}')
            return {'instance': {'state': 'disconnected'}, 'raw': r.text}
        except Exception as e:
            logger.error(f'Erro ao buscar status: {e}')
            return {'instance': {'state': 'error'}}


@router.get('/qr')
async def get_instance_qr():
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.get(f'{EVOLUTION_API_URL}/instance/qr', headers=get_headers())
            logger.info(f'GET /instance/qr -> {r.status_code}: {r.text[:120]}')
            if r.status_code == 200:
                data = r.json()
                qr_val = (
                    data.get('base64')
                    or (data.get('qrcode') or {}).get('base64')
                    or data.get('code')
                    or data.get('qr')
                )
                if qr_val:
                    return {'qrcode': {'base64': qr_val}}
                return data
            if r.status_code == 400:
                return {
                    'error': 'needs_reconnect',
                    'message': 'WhatsApp desconectado. Clique em Reconectar para gerar novo QR Code.'
                }
            return {'error': 'qr_error', 'message': f'Erro ao buscar QR Code ({r.status_code}).'}
        except Exception as e:
            logger.error(f'Erro ao buscar QR: {e}')
            return {'error': 'server_error', 'message': 'Erro de comunicacao com o servidor WhatsApp.'}


@router.post('/reconnect')
async def reconnect_instance():
    async with httpx.AsyncClient(timeout=20.0) as client:
        headers = get_headers()
        try:
            r_logout = await client.delete(f'{EVOLUTION_API_URL}/instance/logout', headers=headers)
            logger.info(f'DELETE /instance/logout -> {r_logout.status_code}: {r_logout.text[:80]}')
        except Exception as e:
            logger.warning(f'Aviso no logout (continuando): {e}')
        await asyncio.sleep(2)
        try:
            r_reconnect = await client.post(f'{EVOLUTION_API_URL}/instance/reconnect', headers=headers)
            logger.info(f'POST /instance/reconnect -> {r_reconnect.status_code}: {r_reconnect.text[:80]}')
            if r_reconnect.status_code in (200, 201):
                return {'status': 'ok', 'message': 'Reconexao iniciada! Aguarde 3 segundos e clique em Gerar QR Code.'}
        except Exception as e:
            logger.warning(f'Aviso no reconnect: {e}')
        return {'status': 'pending', 'message': 'Sessao limpa. Aguarde 3 segundos e clique em Gerar QR Code.'}


@router.delete('/logout')
async def logout_instance():
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.delete(f'{EVOLUTION_API_URL}/instance/logout', headers=get_headers())
            if r.status_code in (200, 204):
                return {'status': 'ok', 'message': 'Instancia desconectada com sucesso'}
            return {'status': 'error', 'message': f'Erro ao desconectar ({r.status_code})'}
        except Exception as e:
            return {'status': 'error', 'message': 'Erro de comunicacao ao desconectar'}

from fastapi import Request
from app.core.security import WEBHOOK_SECRET
from app.services.evolution_api import EVOLUTION_INSTANCE_NAME

@router.post('/fix-webhook')
async def fix_evolution_webhook(request: Request):
    """
    Configura automaticamente o Webhook no GhostHub / Evolution API
    apontando para o backend atual com o token correto.
    """
    # 1. Descobrir a URL base dinamicamente (ex: https://meubackend.railway.app)
    # Como pode estar atras de um proxy (Railway), precisamos garantir https
    forwarded_proto = request.headers.get("x-forwarded-proto", "http")
    forwarded_host = request.headers.get("x-forwarded-host", request.url.hostname)
    base_url = f"{forwarded_proto}://{forwarded_host}"
    
    # Se tiver porta nao padrao (rodando local)
    if request.url.port and request.url.port not in (80, 443) and not request.headers.get("x-forwarded-host"):
        base_url += f":{request.url.port}"
        
    webhook_url = f"{base_url}/api/v1/webhook/evolution?token={WEBHOOK_SECRET}"
    
    payload = {
        "webhook": {
            "url": webhook_url,
            "byEvents": False,
            "base64": False,
            "events": ["MESSAGES_UPSERT"],
            "allowWebhook": True
        }
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.post(f"{EVOLUTION_API_URL}/webhook/set/{EVOLUTION_INSTANCE_NAME}", headers=get_headers(), json=payload)
            logger.info(f"POST /webhook/set -> {r.status_code}: {r.text[:120]}")
            if r.status_code in (200, 201):
                return {"status": "ok", "message": "Webhook corrigido com sucesso!"}
            else:
                # Tenta o formato v1/legacy se o v2 falhar
                payload_v1 = {
                    "enabled": True,
                    "url": webhook_url,
                    "webhookByEvents": False,
                    "events": ["MESSAGES_UPSERT"]
                }
                r_v1 = await client.post(f"{EVOLUTION_API_URL}/webhook/set/{EVOLUTION_INSTANCE_NAME}", headers=get_headers(), json=payload_v1)
                if r_v1.status_code in (200, 201):
                    return {"status": "ok", "message": "Webhook (v1) corrigido com sucesso!"}
                    
                return {"status": "error", "message": f"Falha ao configurar: {r.text}"}
        except Exception as e:
            return {"status": "error", "message": f"Erro de comunicacao com Ghosthub: {str(e)}"}
