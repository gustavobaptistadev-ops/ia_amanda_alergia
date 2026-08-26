from fastapi import APIRouter, HTTPException
import httpx
import logging
from app.services.evolution_api import EVOLUTION_API_URL, get_headers

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/status")
async def get_instance_status():
    """Busca o status da conexão da instância."""
    url = f"{EVOLUTION_API_URL}/instance/status"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=get_headers())
            response.raise_for_status()
            data = response.json()
            print(f">>> [DEBUG] Status Response: {data}", flush=True)
            return data
        except httpx.HTTPError as e:
            logger.error(f"Erro ao buscar status da instância: {e}")
            raise HTTPException(status_code=500, detail="Erro ao se comunicar com a Evolution GO")

@router.get("/qr")
async def get_instance_qr():
    """Busca o QR Code (base64) para conectar o WhatsApp."""
    url = f"{EVOLUTION_API_URL}/instance/qr"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=get_headers())
            response.raise_for_status()
            data = response.json()
            return data
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                # 400 usually means it's already connected or not ready
                return {"error": "already_connected_or_invalid", "message": "Instância já conectada ou erro no QR Code"}
            logger.error(f"Erro HTTP {e.response.status_code} ao buscar QR Code: {e}")
            raise HTTPException(status_code=500, detail="Erro ao gerar QR Code (Bad Request/Not Found)")
        except httpx.HTTPError as e:
            logger.error(f"Erro de comunicação ao buscar QR Code: {e}")
            raise HTTPException(status_code=500, detail="Erro ao gerar QR Code")
