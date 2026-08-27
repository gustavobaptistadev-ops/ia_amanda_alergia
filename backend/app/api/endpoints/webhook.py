from fastapi import APIRouter, Request, BackgroundTasks
import logging
from app.services.evolution_api import send_text_message
from app.core.orchestrator import process_user_message
from app.core.guardrails import validar_resposta
from app.services.db_service import save_message, get_or_create_contact

logger = logging.getLogger(__name__)
router = APIRouter()

async def process_and_respond(remote_jid: str, text: str, push_name: str):
    """Executa a lógica pesada de IA e envia a resposta."""
    try:
        # Salva a mensagem recebida no banco
        await save_message(remote_jid, text, sender='paciente', name=push_name)
        
        from app.api.endpoints.chats import manager
        await manager.broadcast("update")
        
        # Checar se a IA está ativa para este contato
        contact = await get_or_create_contact(remote_jid, push_name)
        if not contact.bot_active:
            print(f">>> [DEBUG] IA ignorou {remote_jid} pois bot_active=False")
            return
            
        if text.strip().lower() == "ping":
            resp = "Pong! O sistema IA Amanda está online e lendo suas mensagens!"
            await send_text_message(remote_jid, resp)
            await save_message(remote_jid, resp, sender='ia')
            return

        # Chamada ao orquestrador (LangGraph) usando o JID como Thread ID (memória)
        ai_response = await process_user_message(thread_id=remote_jid, message=text)
        
        # Validador Final de Segurança (Guardrails)
        is_safe = validar_resposta(ai_response)
        
        if not is_safe:
            ai_response = "Desculpe, por segurança e para estarmos de acordo com a LGPD e o Conselho de Medicina, não posso abordar esse assunto por aqui. Por favor, aguarde que irei transferir você para nossa equipe médica ou ligue para a clínica."

        # Enviar a resposta de volta ao WhatsApp
        await send_text_message(remote_jid, ai_response)
        
        # Salva a resposta enviada no banco
        await save_message(remote_jid, ai_response, sender='ia')
        
        # Avisa o frontend via WebSocket
        from app.api.endpoints.chats import manager
        await manager.broadcast("update")

    except Exception as e:
        print(f">>> [ERROR] Falha ao processar e responder: {e}", flush=True)


async def process_message(data: dict):
    """
    Recebe os webhooks da Evolution API (Ghosthub), extrai os dados da mensagem
    e faz o envio da IA (ou pong) se não for enviada por nós mesmos.
    """
    event_type = data.get("event")
    
    # O Ghosthub dispara o evento "Message" para novas mensagens (na Evolution normal seria "messages.upsert")
    if event_type != "messages.upsert" and event_type != "Message":
        return
    
    try:
        from_me = False
        remote_jid = ""
        push_name = "Cliente"
        text = ""

        # Tenta o formato padrão da Evolution primeiro
        if event_type == "messages.upsert":
            message_data = data.get("data", {})
            message_type = message_data.get("messageType")
            
            # Não processa mensagens enviadas pelo próprio bot ou atualizações de status
            if message_type == "appendMessage" or message_type == "protocolMessage":
                 return
                 
            message_obj = message_data.get("message", {})
            remote_jid = message_data.get("key", {}).get("remoteJid", "")
            from_me = message_data.get("key", {}).get("fromMe", False)
            push_name = message_data.get("pushName", "")
            
            if "conversation" in message_obj:
                text = message_obj["conversation"]
            elif "extendedTextMessage" in message_obj:
                text = message_obj["extendedTextMessage"].get("text", "")
            elif "imageMessage" in message_obj:
                text = message_obj["imageMessage"].get("caption", "")

        # Tenta o formato Ghosthub
        elif event_type == "Message":
            info = data.get("data", {}).get("Info", {})
            msg_obj = data.get("data", {}).get("Message", {})
            
            from_me = info.get("IsFromMe", False)
            remote_jid = info.get("Sender", "")
            if not remote_jid:
                remote_jid = info.get("Chat", "")
            
            push_name = info.get("PushName", "Cliente")
            
            # Ignora mensagens de grupos por enquanto
            if info.get("IsGroup", False):
                 return
                 
            if "conversation" in msg_obj:
                text = msg_obj["conversation"]
            elif "extendedTextMessage" in msg_obj:
                text = msg_obj["extendedTextMessage"].get("text", "")
            elif "imageMessage" in msg_obj:
                text = msg_obj["imageMessage"].get("caption", "")

        # Ignorar se foi a gente mesmo que enviou
        if from_me:
             return
             
        if not text or not remote_jid:
             return

        # Ignorar status de leitura e atualizações do whatsapp
        if "status@broadcast" in remote_jid:
             return

        print(f">>> [DEBUG] Processando Mensagem de {remote_jid}: {text}", flush=True)

        # Chama a função de IA de forma assíncrona
        await process_and_respond(remote_jid, text, push_name)
        
    except Exception as e:
        print(f"Error processing webhook msg: {e}", flush=True)


from arq import create_pool
from arq.connections import RedisSettings
import os
import urllib.parse

# Criação do pool global do Redis para o arq
_redis_pool = None

async def get_redis_pool():
    global _redis_pool
    if _redis_pool is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        parsed = urllib.parse.urlparse(redis_url)
        host = parsed.hostname or 'localhost'
        port = parsed.port or 6379
        password = parsed.password
        database = int(parsed.path.replace('/', '')) if parsed.path and parsed.path != '/' else 0
        redis_settings = RedisSettings(host=host, port=port, password=password, database=database)
        _redis_pool = await create_pool(redis_settings)
    return _redis_pool

@router.post("/evolution")
async def evolution_webhook(request: Request):
    """Webhook para receber eventos da EvolutionAPI / Ghosthub."""
    try:
        data = await request.json()
        print(f">>> [DEBUG] Webhook Payload: {data}", flush=True)
        
        # Enviar o processamento para a fila do Redis (arq) ao invés da memória RAM local
        # Isso garante que não vamos perder mensagens se o servidor reiniciar
        pool = await get_redis_pool()
        await pool.enqueue_job("process_message_job", data)
        
        return {"status": "ok"}
    except Exception as e:
        print(f"Erro no webhook: {e}", flush=True)
        return {"status": "error", "message": str(e)}
