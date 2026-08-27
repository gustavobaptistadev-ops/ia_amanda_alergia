from fastapi import APIRouter, HTTPException
import httpx
import logging
from app.services.evolution_api import EVOLUTION_API_URL, EVOLUTION_INSTANCE_NAME, get_headers

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/status")
async def get_instance_status():
    """Busca o status da conexão da instância."""
    # Ghosthub/Evolution GO might expect instance name in path, or use a custom endpoint
    urls = [
        f"{EVOLUTION_API_URL}/instance/connectionState/{EVOLUTION_INSTANCE_NAME}",
        f"{EVOLUTION_API_URL}/instance/status/{EVOLUTION_INSTANCE_NAME}",
        f"{EVOLUTION_API_URL}/instance/status"
    ]
    
    async with httpx.AsyncClient() as client:
        last_error = None
        for url in urls:
            try:
                response = await client.get(url, headers=get_headers())
                if response.status_code == 200:
                    data = response.json()
                    # Padroniza a resposta para o frontend
                    return data
            except httpx.HTTPError as e:
                last_error = e
                continue
        
        logger.error(f"Erro ao buscar status da instância. Último erro: {last_error}")
        raise HTTPException(status_code=500, detail="Erro ao se comunicar com a Evolution GO")

@router.get("/qr")
async def get_instance_qr():
    """Busca o QR Code (base64) para conectar o WhatsApp."""
    urls = [
        f"{EVOLUTION_API_URL}/instance/connect/{EVOLUTION_INSTANCE_NAME}",
        f"{EVOLUTION_API_URL}/instance/qr/{EVOLUTION_INSTANCE_NAME}",
        f"{EVOLUTION_API_URL}/instance/qr"
    ]
    
    async with httpx.AsyncClient() as client:
        last_error = None
        for url in urls:
            try:
                response = await client.get(url, headers=get_headers())
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 400:
                    return {"error": "already_connected_or_invalid", "message": "Instância já conectada ou erro no QR Code"}
            except httpx.HTTPError as e:
                last_error = e
                continue
                
        logger.error(f"Erro ao buscar QR Code. Último erro: {last_error}")
        raise HTTPException(status_code=500, detail="Erro ao gerar QR Code")

@router.delete("/logout")
async def logout_instance():
    """Desconecta o WhatsApp da instância."""
    urls = [
        f"{EVOLUTION_API_URL}/instance/logout/{EVOLUTION_INSTANCE_NAME}",
        f"{EVOLUTION_API_URL}/instance/logout"
    ]
    
    async with httpx.AsyncClient() as client:
        last_error = None
        for url in urls:
            try:
                response = await client.delete(url, headers=get_headers())
                if response.status_code in [200, 204]:
                    return {"status": "ok", "message": "Instância desconectada com sucesso"}
            except httpx.HTTPError as e:
                last_error = e
                continue
                
        logger.error(f"Erro ao desconectar instância. Último erro: {last_error}")
        raise HTTPException(status_code=500, detail="Erro ao desconectar a instância")

@router.put("/restart")
async def restart_instance():
    """Reinicia a instância na provedora."""
    urls_put = [
        f"{EVOLUTION_API_URL}/instance/restart/{EVOLUTION_INSTANCE_NAME}",
        f"{EVOLUTION_API_URL}/instance/restart"
    ]
    urls_post = [
        f"{EVOLUTION_API_URL}/instance/reconnect",
        f"{EVOLUTION_API_URL}/instance/reconnect/{EVOLUTION_INSTANCE_NAME}"
    ]
    
    async with httpx.AsyncClient() as client:
        last_error = None
        # Tenta PUT primeiro (padrão Evolution)
        for url in urls_put:
            try:
                response = await client.put(url, headers=get_headers())
                if response.status_code in [200, 201]:
                    return {"status": "ok", "message": "Instância reiniciada com sucesso"}
            except httpx.HTTPError as e:
                last_error = e
                continue
                
        # Tenta POST (Ghosthub/Swagger)
        for url in urls_post:
            try:
                response = await client.post(url, headers=get_headers())
                if response.status_code in [200, 201]:
                    return {"status": "ok", "message": "Instância reiniciada com sucesso"}
            except httpx.HTTPError as e:
                last_error = e
                continue
                
        logger.error(f"Erro ao reiniciar instância. Último erro: {last_error}")
        raise HTTPException(status_code=500, detail="Erro ao reiniciar a instância")
