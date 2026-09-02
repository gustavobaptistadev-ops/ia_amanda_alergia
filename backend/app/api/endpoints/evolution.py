from fastapi import APIRouter, HTTPException
import httpx
import logging
from app.services.evolution_api import EVOLUTION_API_URL, EVOLUTION_INSTANCE_NAME, get_headers

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/status")
async def get_instance_status():
    """Busca o status da conexão da instância."""
    url = f"{EVOLUTION_API_URL}/instance/connectionState"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, headers=get_headers())
            if response.status_code == 200:
                return response.json()
            
            # Fallback para endpoint legado
            url_fallback = f"{EVOLUTION_API_URL}/instance/status"
            r2 = await client.get(url_fallback, headers=get_headers())
            if r2.status_code == 200:
                return r2.json()
            
            # Retorna estado desconectado de forma amigável ao frontend (não levanta exceção)
            logger.warning(f"Status da instância retornou {r2.status_code}: {r2.text}")
            return {"instance": {"state": "disconnected"}, "raw": r2.text}
        except httpx.HTTPError as e:
            logger.error(f"Exceção ao buscar status da instância: {e}")
            return {"instance": {"state": "error"}, "detail": str(e)}

@router.get("/qr")
async def get_instance_qr():
    """
    Busca o QR Code para conectar o WhatsApp.
    Quando a instância está em estado 'client disconnected', chama /instance/connect
    para gerar um novo QR Code antes de buscá-lo.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        headers = get_headers()

        # Passo 1: Verifica o estado atual da instância
        state = "unknown"
        try:
            state_resp = await client.get(f"{EVOLUTION_API_URL}/instance/connectionState", headers=headers)
            if state_resp.status_code == 200:
                data = state_resp.json()
                state = (data.get("instance", {}) or data).get("state", "unknown")
                logger.info(f"Estado atual da instância: {state}")
        except Exception as e:
            logger.warning(f"Não foi possível verificar estado da instância: {e}")

        # Passo 2: Se disconnected/close, chama /connect para gerar novo QR
        if state in ("close", "disconnected", "unknown", "connecting"):
            try:
                connect_url = f"{EVOLUTION_API_URL}/instance/connect"
                connect_resp = await client.get(connect_url, headers=headers)
                logger.info(f"Chamada /instance/connect: {connect_resp.status_code} - {connect_resp.text[:120]}")
                if connect_resp.status_code == 200:
                    data = connect_resp.json()
                    # GhostHub pode retornar o QR direto nessa chamada
                    if data.get("base64") or data.get("qrcode") or data.get("code"):
                        qr_val = data.get("base64") or data.get("qrcode") or data.get("code")
                        return {"qrcode": {"base64": qr_val}}
            except Exception as e:
                logger.warning(f"Aviso ao chamar /instance/connect: {e}")

        # Passo 3: Busca o QR Code gerado
        for qr_endpoint in [
            f"{EVOLUTION_API_URL}/instance/qrcode",
            f"{EVOLUTION_API_URL}/instance/qr",
        ]:
            try:
                response = await client.get(qr_endpoint, headers=headers)
                logger.info(f"GET {qr_endpoint} → {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    # Normaliza a resposta para o frontend sempre encontrar o campo correto
                    qr_val = (
                        data.get("base64")
                        or (data.get("qrcode") or {}).get("base64")
                        or data.get("code")
                        or data.get("qr")
                    )
                    if qr_val:
                        return {"qrcode": {"base64": qr_val}}
                    return data  # retorna o que vier se não encontrar campo conhecido
            except Exception as e:
                logger.warning(f"Aviso ao buscar QR em {qr_endpoint}: {e}")
                continue

        # Se chegou aqui, não conseguiu QR — retorna mensagem amigável
        return {
            "error": "qr_unavailable",
            "message": "QR Code indisponível no momento. Aguarde alguns segundos e tente novamente.",
            "hint": "A instância pode estar reconectando. Clique em Reconectar e aguarde 5 segundos."
        }

@router.delete("/logout")
async def logout_instance():
    """Desconecta o WhatsApp da instância."""
    url = f"{EVOLUTION_API_URL}/instance/logout"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
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
    """
    Força reconexão da instância — útil quando o WhatsApp foi desconectado pelo celular.
    Chama /instance/connect (correto para estado client_disconnected) e depois /instance/reconnect como fallback.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        headers = get_headers()
        
        # Tenta /instance/connect primeiro (correto para client disconnected)
        for endpoint, method in [
            (f"{EVOLUTION_API_URL}/instance/connect", "GET"),
            (f"{EVOLUTION_API_URL}/instance/reconnect", "POST"),
        ]:
            try:
                if method == "GET":
                    response = await client.get(endpoint, headers=headers)
                else:
                    response = await client.post(endpoint, headers=headers)
                    
                logger.info(f"{method} {endpoint} → {response.status_code}: {response.text[:80]}")
                if response.status_code in [200, 201]:
                    return {"status": "ok", "message": "Instância reconectando. Aguarde o QR Code aparecer.", "data": response.json()}
            except Exception as e:
                logger.warning(f"Aviso em {endpoint}: {e}")
                continue

        return {"status": "warning", "message": "Reconexão iniciada. Se o QR não aparecer em 10 segundos, tente novamente."}

