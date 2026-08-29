from app.services.evolution_api import send_text_message
from app.core.orchestrator import process_user_message
from app.core.guardrails import validar_resposta
from app.services.db_service import save_message, get_or_create_contact
import logging

logger = logging.getLogger(__name__)

async def process_and_respond(remote_jid: str, text: str, push_name: str):
    """Executa a logica pesada de IA e envia a resposta."""
    try:
        await save_message(remote_jid, text, sender='paciente', name=push_name)
        
        from app.api.endpoints.chats import manager
        await manager.broadcast("update")
        
        contact = await get_or_create_contact(remote_jid, push_name)
        if not contact.bot_active:
            print(f">>> [DEBUG] IA ignorou {remote_jid} pois bot_active=False")
            return
            
        if text.strip().lower() == "ping":
            resp = "Pong! O sistema IA Amanda esto online e lendo suas mensagens!"
            await send_text_message(remote_jid, resp)
            await save_message(remote_jid, resp, sender='ia')
            return

        ai_response = await process_user_message(thread_id=remote_jid, message=text)
        is_safe = validar_resposta(ai_response)
        
        if not is_safe:
            ai_response = "Desculpe, por segurana e para estarmos de acordo com a LGPD e o Conselho de Medicina, nuo posso abordar esse assunto por aqui. Por favor, aguarde que irei transferir vocG para nossa equipe m?dica ou ligue para a clnica."

        await send_text_message(remote_jid, ai_response)
        await save_message(remote_jid, ai_response, sender='ia')
        
        from app.api.endpoints.chats import manager
        await manager.broadcast("update")

    except Exception as e:
        print(f">>> [ERROR] Falha ao processar e responder: {e}", flush=True)

async def process_message(data: dict):
    """Extrai os dados da mensagem do payload Ghosthub e aciona o process_and_respond"""
    event_type = data.get("event")
    
    if event_type != "messages.upsert" and event_type != "Message":
        return
    
    try:
        from_me = False
        remote_jid = ""
        push_name = "Cliente"
        text = ""

        if event_type == "messages.upsert":
            message_data = data.get("data", {})
            message_type = message_data.get("messageType")
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

        elif event_type == "Message":
            info = data.get("data", {}).get("Info", {})
            msg_obj = data.get("data", {}).get("Message", {})
            from_me = info.get("IsFromMe", False)
            remote_jid = info.get("Sender", "")
            if not remote_jid:
                remote_jid = info.get("Chat", "")
            push_name = info.get("PushName", "Cliente")
            if info.get("IsGroup", False):
                 return
            if "conversation" in msg_obj:
                text = msg_obj["conversation"]
            elif "extendedTextMessage" in msg_obj:
                text = msg_obj["extendedTextMessage"].get("text", "")
            elif "imageMessage" in msg_obj:
                text = msg_obj["imageMessage"].get("caption", "")

        if from_me:
             return
        if not text or not remote_jid:
             return
        if "status@broadcast" in remote_jid:
             return

        logger.info(f"Processando Mensagem do paciente terminada em ...{remote_jid[-4:]} | Tamanho do texto: {len(text)} caracteres")
        await process_and_respond(remote_jid, text, push_name)
        
    except Exception as e:
        print(f"Error processing webhook msg: {e}", flush=True)
