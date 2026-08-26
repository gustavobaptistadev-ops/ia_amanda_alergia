import httpx
import os
import logging

logger = logging.getLogger(__name__)

EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "sua_api_key_aqui")
EVOLUTION_INSTANCE_NAME = os.getenv("EVOLUTION_INSTANCE_NAME", "ia_amanda")

def get_headers():
    return {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json",
        "instance": EVOLUTION_INSTANCE_NAME # Algumas versões exigem o nome da instância no header
    }

async def send_text_message(number: str, text: str):
    """Envia uma mensagem de texto via EvolutionAPI."""
    url = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE_NAME}"
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
