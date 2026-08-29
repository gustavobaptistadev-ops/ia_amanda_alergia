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
            ai_response = "Desculpe, por segurança e para estarmos de acordo com a LGPD e o Conselho de Medicina, não posso abordar esse assunto por aqui. Por favor, aguarde que irei transferir você para nossa equipe médica ou ligue para a clínica."

        if "⚠️ Identifiquei que você pode estar passando por uma situação de urgência" in ai_response:
            logger.warning(f"Urgência detectada para {remote_jid}. Pausando IA e escalando para atendimento humano...")
            from app.database import AsyncSessionLocal
            from app.models.chat import Contact
            from sqlalchemy.future import select
            
            async with AsyncSessionLocal() as session:
                res = await session.execute(select(Contact).where(Contact.phone_number == remote_jid))
                c = res.scalars().first()
                if c:
                    c.bot_active = False
                    c.stage = "atendimento_humano"
                    await session.commit()

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
            elif "audioMessage" in message_obj:
                logger.info("Detectada mensagem de áudio (messages.upsert). Iniciando transcrição...")
                from app.services.audio_service import transcribe_audio_from_base64_or_url, download_audio_from_url
                import base64
                
                audio_data = message_obj["audioMessage"]
                # Caso venha base64 direto ou url
                if "base64" in audio_data:
                    raw_audio = base64.b64decode(audio_data["base64"])
                    text = await transcribe_audio_from_base64_or_url(raw_audio)
                elif "url" in audio_data:
                    raw_audio = await download_audio_from_url(audio_data["url"])
                    if raw_audio:
                        text = await transcribe_audio_from_base64_or_url(raw_audio)

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
            elif "audioMessage" in msg_obj:
                logger.info("Detectada mensagem de áudio (Message). Iniciando transcrição...")
                from app.services.audio_service import transcribe_audio_from_base64_or_url, download_audio_from_url
                import base64
                
                audio_data = msg_obj["audioMessage"]
                if "base64" in audio_data:
                    raw_audio = base64.b64decode(audio_data["base64"])
                    text = await transcribe_audio_from_base64_or_url(raw_audio)
                elif "url" in audio_data:
                    raw_audio = await download_audio_from_url(audio_data["url"])
                    if raw_audio:
                        text = await transcribe_audio_from_base64_or_url(raw_audio)

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
