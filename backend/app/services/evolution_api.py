import httpx
import os
import logging

logger = logging.getLogger(__name__)

EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
# A chave global enviada pelo CTO
EVOLUTION_GLOBAL_KEY = os.getenv("EVOLUTION_GLOBAL_KEY", "1dcd4e3bc54541449f52c5e319d7eeda")
# O token que queremos injetar na nossa instância
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "chave-secreta-ia-amanda")
EVOLUTION_INSTANCE_NAME = os.getenv("EVOLUTION_INSTANCE_NAME", "ia_amanda")

def get_headers():
    return {
        "apikey": EVOLUTION_API_KEY,
        "Authorization": f"Bearer {EVOLUTION_API_KEY}",
        "Content-Type": "application/json",
        "instance": EVOLUTION_INSTANCE_NAME
    }

async def auto_create_instance():
    """Tenta criar a instância na inicialização usando a Global Key, para todos os tenants no banco."""
    from app.database import AsyncSessionLocal
    from app.models.tenant import Tenant
    from sqlalchemy import select
    
    url = f"{EVOLUTION_API_URL}/instance/create"
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Tenant).where(Tenant.is_active == True))
        tenants = result.scalars().all()
        
        # Fallback de retrocompatibilidade (para o bot ia_amanda inicial se a tabela estiver vazia)
        if not tenants:
            logger.info("Nenhum tenant encontrado no banco. Criando tenant padrão.")
            default_tenant = Tenant(
                name="Clínica Alergia Matriz",
                instance_name=EVOLUTION_INSTANCE_NAME,
                instance_token=EVOLUTION_API_KEY
            )
            db.add(default_tenant)
            await db.commit()
            tenants = [default_tenant]
            
    async with httpx.AsyncClient() as client:
        for tenant in tenants:
            headers = {
                "apikey": EVOLUTION_GLOBAL_KEY,
                "Content-Type": "application/json"
            }
            payload = {
                "name": tenant.instance_name,
                "token": tenant.instance_token,
                "qrcode": True
            }
            try:
                logger.info(f"Verificando/Criando instância '{tenant.instance_name}' via Global Key...")
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    logger.info(f"Instância '{tenant.instance_name}' criada com sucesso!")
                elif res.status_code == 500 and "already exists" in res.text.lower():
                    logger.info(f"Instância '{tenant.instance_name}' já existe. Usando a existente.")
                else:
                    logger.warning(f"Aviso ao criar instância: {res.status_code} - {res.text}")
            except Exception as e:
                logger.error(f"Erro ao tentar criar instância '{tenant.instance_name}': {e}")

async def send_text_message(number: str, text: str):
    """Envia uma mensagem de texto via EvolutionAPI."""
    url = f"{EVOLUTION_API_URL}/send/text"
    payload = {
        "number": number,
        "text": text,
        "delay": 1200 # 1.2 segundos de delay digitando
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=get_headers())
            response.raise_for_status()
            logger.info(f"Mensagem enviada para {number} com sucesso.")
            return response.json()
        except httpx.HTTPError as e:
            error_body = e.response.text if hasattr(e, 'response') and e.response else "No response body"
            logger.error(f"Erro ao enviar mensagem para {number}: {e} | Body: {error_body}")
            return None

async def send_voice_audio_message(number: str, audio_bytes: bytes):
    """Envia uma mensagem de áudio (formato de nota de voz WhatsApp) via EvolutionAPI / Ghosthub."""
    import base64
    if not audio_bytes:
        return None

    b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
    
    # 1. Tenta endpoint padrão /send/media
    url = f"{EVOLUTION_API_URL}/send/media"
    payload = {
        "number": number,
        "media": f"data:audio/ogg;base64,{b64_audio}",
        "mediatype": "audio",
        "delay": 1500
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, json=payload, headers=get_headers())
            if response.status_code == 200:
                logger.info(f"Áudio de voz enviado para {number} com sucesso via /send/media.")
                return response.json()
            else:
                logger.warning(f"Aviso /send/media ({response.status_code}): {response.text}. Tentando endpoint alternativo /send/audio...")
                
                # 2. Fallback para /send/audio (se suportado pelo provedor Ghosthub)
                alt_url = f"{EVOLUTION_API_URL}/send/audio"
                alt_payload = {
                    "number": number,
                    "audio": f"data:audio/ogg;base64,{b64_audio}",
                    "delay": 1500
                }
                alt_res = await client.post(alt_url, json=alt_payload, headers=get_headers())
                if alt_res.status_code == 200:
                    logger.info(f"Áudio de voz enviado para {number} com sucesso via /send/audio.")
                    return alt_res.json()
                return None
        except Exception as e:
            logger.error(f"Erro ao enviar áudio para {number}: {e}")
            return None

async def get_base64_from_media(message_id: str, remote_jid: str = "", message_obj: dict = None) -> bytes:
    """Busca o base64 de uma mensagem de mídia na EvolutionAPI / Ghosthub."""
    import base64
    if not message_id and not message_obj:
        return None

    headers = get_headers()
    
    # Lista de endpoints suportados por diferentes versões da Evolution / Ghosthub
    endpoints = [
        f"{EVOLUTION_API_URL}/chat/getBase64FromMediaMessage",
        f"{EVOLUTION_API_URL}/message/getBase64FromMediaMessage",
        f"{EVOLUTION_API_URL}/messages/getBase64"
    ]
    
    payloads = [
        {
            "message": {
                "key": {
                    "id": message_id,
                    "remoteJid": remote_jid
                }
            },
            "convertToMp4": False
        },
        {
            "id": message_id,
            "remoteJid": remote_jid
        }
    ]

    async with httpx.AsyncClient(timeout=30.0) as client:
        for url in endpoints:
            for p in payloads:
                try:
                    res = await client.post(url, json=p, headers=headers)
                    if res.status_code == 200:
                        data = res.json()
                        b64_str = data.get("base64") or data.get("media") or data.get("data") or ""
                        if b64_str:
                            if "," in b64_str:
                                b64_str = b64_str.split(",")[1]
                            logger.info(f"Mídia recuperada e descriptografada com sucesso via {url}")
                            return base64.b64decode(b64_str)
                except Exception as e:
                    pass

    return None
