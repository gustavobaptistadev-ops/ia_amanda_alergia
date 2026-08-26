from fastapi import APIRouter, Request, BackgroundTasks
import logging
from app.services.evolution_api import send_text_message

logger = logging.getLogger(__name__)
router = APIRouter()

async def process_message(data: dict):
    """Processa a mensagem recebida de forma assíncrona."""
    try:
        # A estrutura do webhook depende do evento configurado na EvolutionAPI.
        # Geralmente mensagens chegam no evento "messages.upsert"
        event = data.get("event")
        
        if event == "messages.upsert":
            messages = data.get("data", {}).get("message", {})
            # Ignorar mensagens enviadas pelo próprio bot (fromMe)
            from_me = data.get("data", {}).get("key", {}).get("fromMe", False)
            
            if from_me:
                return

            remote_jid = data.get("data", {}).get("key", {}).get("remoteJid", "")
            
            # Pega o texto da mensagem (pode ser text, conversation, extendedTextMessage...)
            message_type = data.get("data", {}).get("messageType")
            text = ""
            
            if message_type == "conversation":
                text = messages.get("conversation", "")
            elif message_type == "extendedTextMessage":
                text = messages.get("extendedTextMessage", {}).get("text", "")
                
            logger.info(f"Mensagem recebida de {remote_jid[:4]}***{remote_jid[-8:]}: {text}")
            
            # Ping / Pong de teste ou chamada à IA
            if text and text.strip().lower() == "ping":
                await send_text_message(remote_jid, "Pong! O sistema IA Amanda está online.")
            elif text:
                # Chamada ao orquestrador (LangGraph) usando o JID como Thread ID (memória)
                from app.core.orchestrator import process_user_message
                from app.core.guardrails import validar_resposta
                
                ai_response = await process_user_message(thread_id=remote_jid, message=text)
                
                # Validador Final de Segurança (Guardrails)
                is_safe = validar_resposta(ai_response)
                
                if not is_safe:
                    ai_response = "Desculpe, por segurança e para estarmos de acordo com a LGPD e o Conselho de Medicina, não posso abordar esse assunto por aqui. Por favor, aguarde que irei transferir você para nossa equipe médica ou ligue para a clínica."
                
                # Enviar a resposta de volta ao WhatsApp
                await send_text_message(remote_jid, ai_response)
                
    except Exception as e:
        logger.error(f"Erro ao processar mensagem do webhook: {e}")

@router.post("/evolution")
async def evolution_webhook(request: Request, background_tasks: BackgroundTasks):
    """Webhook para receber eventos da EvolutionAPI."""
    try:
        data = await request.json()
        print(f">>> [DEBUG] Webhook Payload: {data}", flush=True)
        
        # Processar a mensagem em background para liberar o webhook rapidamente
        background_tasks.add_task(process_message, data)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Erro no webhook: {e}")
        return {"status": "error", "message": str(e)}
