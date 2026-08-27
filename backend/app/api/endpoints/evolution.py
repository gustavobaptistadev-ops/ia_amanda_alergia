from fastapi import APIRouter, HTTPException
import httpx
import logging
from app.services.evolution_api import EVOLUTION_API_URL, EVOLUTION_INSTANCE_NAME, get_headers

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/status")
async def get_instance_status():
    """Busca o status da conexão da instância."""
    url = f"{EVOLUTION_API_URL}/instance/status"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=get_headers())
            if response.status_code == 200:
                return response.json()
            
            logger.error(f"Erro ao buscar status: {response.status_code} - {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Erro ao se comunicar com a Evolution GO")
        except httpx.HTTPError as e:
            logger.error(f"Exceção ao buscar status da instância: {e}")
            raise HTTPException(status_code=500, detail="Erro interno ao se comunicar com a Evolution GO")

@router.get("/qr")
async def get_instance_qr():
    """Busca o QR Code (base64) para conectar o WhatsApp."""
    url = f"{EVOLUTION_API_URL}/instance/qr"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=get_headers())
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 400:
                return {"error": "already_connected_or_invalid", "message": "Instância já conectada ou erro no QR Code"}
                
            logger.error(f"Erro ao buscar QR Code: {response.status_code} - {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Erro ao gerar QR Code")
        except httpx.HTTPError as e:
            logger.error(f"Exceção ao buscar QR Code: {e}")
            raise HTTPException(status_code=500, detail="Erro interno ao gerar QR Code")

@router.delete("/logout")
async def logout_instance():
    """Desconecta o WhatsApp da instância."""
    url = f"{EVOLUTION_API_URL}/instance/logout"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(url, headers=get_headers())
            if response.status_code in [200, 204]:
                return {"status": "ok", "message": "Instância desconectada com sucesso"}
                
            logger.error(f"Erro ao desconectar: {response.status_code} - {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Erro ao desconectar a instância")
        except httpx.HTTPError as e:
            logger.error(f"Exceção ao desconectar: {e}")
            raise HTTPException(status_code=500, detail="Erro interno ao desconectar a instância")

@router.post("/reconnect")
async def reconnect_instance():
    """Reinicia/Reconecta a instância na provedora."""
    url = f"{EVOLUTION_API_URL}/instance/reconnect"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=get_headers())
            if response.status_code in [200, 201]:
                return {"status": "ok", "message": "Instância reiniciada com sucesso"}
                
            logger.error(f"Erro ao reiniciar: {response.status_code} - {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Erro ao reiniciar a instância")
        except httpx.HTTPError as e:
            logger.error(f"Exceção ao reiniciar: {e}")
            raise HTTPException(status_code=500, detail="Erro interno ao reiniciar a instância")
