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
    """Tenta criar a instância na inicialização usando a Global Key."""
    url = f"{EVOLUTION_API_URL}/instance/create"
    headers = {
        "apikey": EVOLUTION_GLOBAL_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "name": EVOLUTION_INSTANCE_NAME,
        "token": EVOLUTION_API_KEY,
        "qrcode": True
    }
    
    async with httpx.AsyncClient() as client:
        try:
            logger.info(f"Verificando/Criando instância '{EVOLUTION_INSTANCE_NAME}' via Global Key...")
            res = await client.post(url, headers=headers, json=payload)
            if res.status_code == 200:
                logger.info(f"Instância '{EVOLUTION_INSTANCE_NAME}' criada com sucesso!")
            elif res.status_code == 500 and "already exists" in res.text.lower():
                logger.info(f"Instância '{EVOLUTION_INSTANCE_NAME}' já existe. Usando a existente.")
            else:
                logger.warning(f"Aviso ao criar instância: {res.status_code} - {res.text}")
        except Exception as e:
            logger.error(f"Erro ao tentar criar instância automaticamente: {e}")

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
            logger.error(f"Erro ao enviar mensagem para {number}: {e}")
            return None
