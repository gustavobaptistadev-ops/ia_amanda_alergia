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
            logger.info(f"Status Response: {data}")
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
        except httpx.HTTPError as e:
            logger.error(f"Erro ao buscar QR Code da instância: {e}")
            raise HTTPException(status_code=500, detail="Erro ao gerar QR Code")
