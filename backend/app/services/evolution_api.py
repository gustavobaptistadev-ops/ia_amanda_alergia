import logging
import os
import re

import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

EMOJI_PATTERN = re.compile(
    "[\\U0001F1E6-\\U0001F1FF\\U0001F300-\\U0001FAFF\\u2600-\\u27BF]"
)


def remove_emojis(text: str) -> str:
    """Keep outbound patient messages free of emoji characters."""
    if not text:
        return text
    return EMOJI_PATTERN.sub("", text).replace("\ufe0f", "").replace("\u200d", "")


def repair_mojibake(text: str) -> str:
    """Corrige texto legado salvo com UTF-8 interpretado como Windows-1252."""
    if not text or not any(marker in text for marker in ("Ã", "Â", "â", "ð", "�")):
        return text
    repaired = text
    for _ in range(3):
        try:
            candidate = repaired.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            break
        if candidate == repaired:
            break
        repaired = candidate
        if not any(marker in repaired for marker in ("Ã", "Â", "â", "ð", "�")):
            break
    return repaired


EVOLUTION_API_URL = settings.EVOLUTION_API_URL
EVOLUTION_GLOBAL_KEY = settings.EVOLUTION_GLOBAL_KEY.strip()
EVOLUTION_API_KEY = settings.EVOLUTION_API_KEY.strip()
EVOLUTION_INSTANCE_NAME = settings.EVOLUTION_INSTANCE_NAME

_cached_tenant_token = None


def get_headers():
    token = settings.EVOLUTION_API_KEY.strip() or EVOLUTION_API_KEY
    if not token:
        raise RuntimeError("EVOLUTION_API_KEY must be configured")

    return {
        "apikey": token,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "instance": EVOLUTION_INSTANCE_NAME,
    }


async def auto_create_instance():
    """Tenta criar a instância na inicialização usando a Global Key, para todos os tenants no banco."""
    if not EVOLUTION_GLOBAL_KEY:
        raise RuntimeError("EVOLUTION_GLOBAL_KEY must be configured")
    from sqlalchemy import select

    from app.database import AsyncSessionLocal
    from app.models.tenant import Tenant

    url = f"{EVOLUTION_API_URL}/instance/create"

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Tenant).where(Tenant.is_active == True))
        tenants = result.scalars().all()

        # Fallback de retrocompatibilidade (para o bot ia_amanda inicial se a tabela estiver vazia)
        if not tenants:
            logger.info("Nenhum tenant encontrado no banco. Criando tenant padrão.")
            default_tenant = Tenant(
                name="Clínica Lifeline One",
                instance_name=EVOLUTION_INSTANCE_NAME,
                instance_token=EVOLUTION_API_KEY,
            )
            db.add(default_tenant)
            await db.commit()
            tenants = [default_tenant]

    async with httpx.AsyncClient(timeout=15.0) as client:
        for tenant in tenants:
            headers = {"apikey": EVOLUTION_GLOBAL_KEY, "Content-Type": "application/json"}
            payload = {
                "instanceName": tenant.instance_name,
                "token": tenant.instance_token,
                "qrcode": True,
                "integration": "WHATSAPP-BAILEYS",
            }
            try:
                logger.info(
                    f"Verificando/Criando instância '{tenant.instance_name}' via Global Key..."
                )
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    logger.info(f"Instância '{tenant.instance_name}' criada com sucesso!")
                elif res.status_code == 500 and "already exists" in res.text.lower():
                    logger.info(
                        f"Instância '{tenant.instance_name}' já existe. Usando a existente."
                    )
                else:
                    logger.warning(
                        f"Aviso ao criar instância: {res.status_code} - {res.text}"
                    )
            except Exception as e:
                logger.error(
                    "Erro ao tentar criar instância '%s': %s",
                    tenant.instance_name,
                    type(e).__name__,
                )


async def send_text_message(number: str, text: str):
    """Envia uma mensagem de texto via EvolutionAPI."""
    text = remove_emojis(text)
    url = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE_NAME}"
    payload = {"number": number, "text": text, "delay": 1200, "options": {"delay": 1200}}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=get_headers())
            response.raise_for_status()
            logger.info(f"Mensagem enviada para {number} com sucesso.")
            return response.json()
        except httpx.HTTPError as e:
            error_body = (
                e.response.text
                if hasattr(e, "response") and e.response
                else "No response body"
            )
            logger.error(
                f"Erro ao enviar mensagem para {number}: {e} | Body: {error_body}"
            )
            return None


async def send_voice_audio_message(number: str, audio_bytes: bytes):
    """Envia uma mensagem de áudio (formato de nota de voz WhatsApp) via EvolutionAPI."""
    import base64

    if not audio_bytes:
        return None

    b64_audio = base64.b64encode(audio_bytes).decode("utf-8")

    url = f"{EVOLUTION_API_URL}/message/sendWhatsAppAudio/{EVOLUTION_INSTANCE_NAME}"
    payload = {
        "number": number,
        "audio": f"data:audio/ogg;base64,{b64_audio}",
        "delay": 1500,
        "options": {"delay": 1500},
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, json=payload, headers=get_headers())
            if response.status_code == 200:
                logger.info(
                    f"Áudio de voz enviado para {number} com sucesso via /send/media."
                )
                return response.json()
            else:
                logger.warning(
                    f"Aviso /send/media ({response.status_code}): {response.text}. Tentando endpoint alternativo /send/audio..."
                )

                # 2. Fallback para media
                alt_url = (
                    f"{EVOLUTION_API_URL}/message/sendMedia/{EVOLUTION_INSTANCE_NAME}"
                )
                alt_payload = {
                    "number": number,
                    "media": f"data:audio/ogg;base64,{b64_audio}",
                    "mediatype": "audio",
                    "delay": 1500,
                    "options": {"delay": 1500},
                }
                alt_res = await client.post(
                    alt_url, json=alt_payload, headers=get_headers()
                )
                if alt_res.status_code == 200:
                    logger.info(
                        f"Áudio de voz enviado para {number} com sucesso via /send/audio."
                    )
                    return alt_res.json()
                return None
        except Exception as e:
            logger.error(f"Erro ao enviar áudio para {number}: {e}")
            return None


async def send_document_message(
    number: str, document_bytes: bytes, filename: str, caption: str = ""
):
    """Envia um arquivo (documento) via EvolutionAPI."""
    import base64

    if not document_bytes:
        return None

    b64_doc = base64.b64encode(document_bytes).decode("utf-8")

    url = f"{EVOLUTION_API_URL}/message/sendMedia/{EVOLUTION_INSTANCE_NAME}"
    payload = {
        "number": number,
        "media": f"data:text/calendar;base64,{b64_doc}",
        "mediatype": "document",
        "fileName": filename,
        "caption": caption,
        "delay": 1500,
        "options": {"delay": 1500},
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, json=payload, headers=get_headers())
            if response.status_code == 200 or response.status_code == 201:
                logger.info(f"Documento enviado para {number} com sucesso.")
                return response.json()
            else:
                logger.warning(
                    f"Aviso ao enviar documento para {number} ({response.status_code}): {response.text}"
                )
                return None
        except Exception as e:
            logger.error(f"Erro ao enviar documento para {number}: {e}")
            return None


async def get_base64_from_media(
    message_id: str, remote_jid: str = "", message_obj: dict = None
) -> bytes:
    """Busca o base64 de uma mensagem de mídia na EvolutionAPI / Ghosthub."""
    import base64

    if not message_id and not message_obj:
        raise Exception("Nenhum message_id ou message_obj fornecido")

    headers = get_headers()

    endpoints = [
        f"{EVOLUTION_API_URL}/chat/getBase64FromMediaMessage/{EVOLUTION_INSTANCE_NAME}",
        f"{EVOLUTION_API_URL}/message/getBase64FromMediaMessage/{EVOLUTION_INSTANCE_NAME}",
        f"{EVOLUTION_API_URL}/chat/getBase64FromMediaMessage",
        f"{EVOLUTION_API_URL}/message/getBase64FromMediaMessage",
    ]

    payloads = []
    if message_obj:
        payloads.append({
            "message": message_obj,
            "convertToMp4": False,
        })
    payloads.extend([
        {
            "message": {"key": {"id": message_id, "remoteJid": remote_jid}},
            "convertToMp4": False,
        },
        {"id": message_id, "remoteJid": remote_jid},
    ])

    errors = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for url in endpoints:
            for p in payloads:
                try:
                    res = await client.post(url, json=p, headers=headers)
                    if res.status_code == 200:
                        data = res.json()
                        b64_str = (
                            data.get("base64")
                            or data.get("media")
                            or data.get("data")
                            or ""
                        )
                        if b64_str:
                            if "," in b64_str:
                                b64_str = b64_str.split(",")[1]
                            return base64.b64decode(b64_str)
                        else:
                            errors.append(f"{url} [200 OK] mas base64/media/data ausente no JSON.")
                    else:
                        errors.append(f"{url} [{res.status_code}] {res.text[:100]}")
                except Exception as e:
                    errors.append(f"{url} Erro de requisição: {str(e)}")

    raise Exception(" | ".join(errors))


    headers = get_headers()

    # Lista de endpoints suportados por diferentes versões da Evolution / Ghosthub
    endpoints = [
        f"{EVOLUTION_API_URL}/chat/getBase64FromMediaMessage/{EVOLUTION_INSTANCE_NAME}",
        f"{EVOLUTION_API_URL}/message/getBase64FromMediaMessage/{EVOLUTION_INSTANCE_NAME}",
        f"{EVOLUTION_API_URL}/chat/getBase64FromMediaMessage",
        f"{EVOLUTION_API_URL}/message/getBase64FromMediaMessage",
    ]

    payloads = []
    if message_obj:
        payloads.append({
            "message": message_obj,
            "convertToMp4": False,
        })
    payloads.extend([
        {
            "message": {"key": {"id": message_id, "remoteJid": remote_jid}},
            "convertToMp4": False,
        },
        {"id": message_id, "remoteJid": remote_jid},
    ])

    async with httpx.AsyncClient(timeout=30.0) as client:
        for url in endpoints:
            for p in payloads:
                try:
                    res = await client.post(url, json=p, headers=headers)
                    if res.status_code == 200:
                        data = res.json()
                        b64_str = (
                            data.get("base64")
                            or data.get("media")
                            or data.get("data")
                            or ""
                        )
                        if b64_str:
                            if "," in b64_str:
                                b64_str = b64_str.split(",")[1]
                            logger.info(
                                f"Mídia recuperada e descriptografada com sucesso via {url}"
                            )
                            return base64.b64decode(b64_str)
                except Exception:
                    pass

    return None
