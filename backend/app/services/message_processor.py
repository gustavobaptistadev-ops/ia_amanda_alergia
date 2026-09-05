import logging

from app.core.guardrails import validar_resposta
from app.core.limiter import check_phone_rate_limit
from app.core.orchestrator import process_user_message
from app.services.db_service import get_or_create_contact, save_message
from app.services.evolution_api import remove_emojis, repair_mojibake, send_text_message

logger = logging.getLogger(__name__)


import redis.asyncio as redis
from app.core.config import settings

REDIS_URL = settings.REDIS_URL

redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


from app.core.input_shield import detect_emergency, EMERGENCY_RESPONSE, detect_adversarial_attempt

async def process_and_respond(
    remote_jid: str, text: str, push_name: str, is_audio: bool = False
):
    """Executa a logica pesada de IA e envia a resposta de forma estritamente sequencial (lock distribuído via Redis)."""

    # [SEGURANÇA 1.1] Rate Limit por número de telefone — protege contra DDoS semântico

    is_rate_limited = await check_phone_rate_limit(remote_jid, max_per_minute=20)

    if is_rate_limited:
        logger.warning(
            f"Rate limit atingido para {remote_jid[:6]}****. Mensagem ignorada."
        )

        await send_text_message(
            remote_jid,
            "Estou recebendo muitas mensagens em seguida. Aguarde um momento e tente novamente!",
        )
        return

    # [SEGURANÇA 2.3] Triagem de Emergência — detecta urgência real ANTES do processamento da IA

    if detect_emergency(text):
        logger.warning(
            f"TRIAGEM DE EMERGÊNCIA acionada para {remote_jid[:6]}****. Enviando resposta de segurança imediata."
        )

        await send_text_message(remote_jid, EMERGENCY_RESPONSE)

        await save_message(remote_jid, text, sender="paciente", name=push_name)

        await save_message(remote_jid, remove_emojis(EMERGENCY_RESPONSE), sender="ia")
        from app.database import AsyncSessionLocal
        from app.models.chat import SystemLog

        async with AsyncSessionLocal() as session:
            session.add(
                SystemLog(
                    category="triagem_emergencia",
                    level="ALERTA",
                    title=f"Emergência detectada: {push_name or remote_jid[:6]}****",
                    detail=f"Gatilho: '{text[:80]}' | JID: {remote_jid[:6]}****",
                )
            )

            await session.commit()

        return

    # Lock distribuído (timeout: liberta a trava se o worker morrer; blocking_timeout: aguarda até 2 mins por outra msg terminar)

    async with redis_client.lock(
        f"lock:patient:{remote_jid}", timeout=180, blocking_timeout=120
    ):
        try:
            await save_message(remote_jid, text, sender="paciente", name=push_name)

            from app.api.endpoints.chats import manager

            await manager.broadcast("update")

            contact = await get_or_create_contact(remote_jid, push_name)

            if not contact.bot_active:
                print(f">>> [DEBUG] IA ignorou {remote_jid} pois bot_active=False")

                return

            if text.strip().lower() == "ping":
                resp = "Pong! O sistema IA Amanda esto online e lendo suas mensagens!"

                await send_text_message(remote_jid, resp)

                await save_message(remote_jid, resp, sender="ia")

                return

            if await detect_adversarial_attempt(text):
                logger.warning(f"Interceptado pelo Input Shield: {remote_jid}")
                ai_response = "Por diretrizes de segurança da clínica, não posso responder a esta solicitação. Como posso ajudar com sua saúde ou agendamento?"
                await send_text_message(remote_jid, ai_response)
                await save_message(remote_jid, ai_response, sender="ia")
                return

            try:
                ai_response = await process_user_message(
                    thread_id=remote_jid, message=text
                )

            except Exception:
                logger.exception("Erro ao processar mensagem para %s", remote_jid[:6])
                ai_response = "Nosso sistema está passando por uma instabilidade momentânea. Um de nossos atendentes humanos já foi notificado e falará com você em breve."

            # Normaliza respostas antigas antes do filtro final e do envio ao WhatsApp.
            ai_response = repair_mojibake(remove_emojis(ai_response))
            is_safe = validar_resposta(ai_response)

            if not is_safe:
                # Se for bloqueio real de segurança (prescrição ou jailbreak), responde com prudência médica
                ai_response = "Por diretrizes do Conselho de Medicina e segurança clínica, prescrições de remédios e orientações de posologia são realizadas exclusivamente pelo médico durante a sua consulta. Posso te ajudar a agendar um horário com nossos especialistas?"

            if is_safe:
                from app.services.semantic_cache import set_cached_response

                await set_cached_response(text, ai_response)

            if (
                "Identifiquei que você pode estar passando por uma situação de urgência"
                in ai_response
                or "[TRANSFERIR_HUMANO]" in ai_response
            ):
                logger.warning(f"Escalando para atendimento humano: {remote_jid}")
                from app.services.db_service import update_contact_bot_active, update_contact_stage_by_phone
                
                # Remover a tag secreta antes de enviar ao paciente
                ai_response = ai_response.replace("[TRANSFERIR_HUMANO]", "").strip()

                await update_contact_bot_active(remote_jid, False)
                await update_contact_stage_by_phone(remote_jid, "atendimento_humano")

                # Disparar alerta visual/sonoro via WebSocket

                await manager.broadcast(f"urgency:{remote_jid}")

            # [MULTIMODAL] Se o paciente mandou áudio e a opção de voz estiver ligada, responder com áudio TTS

            from app.api.endpoints.settings import load_config

            cfg = load_config()

            voice_enabled = cfg.get("voice_reply_enabled", False)

            if is_audio and voice_enabled:
                from app.services.evolution_api import send_voice_audio_message
                from app.services.tts_service import generate_speech_audio

                voice_name = cfg.get("voice_name", "nova")

                audio_bytes = await generate_speech_audio(ai_response, voice=voice_name)

                if audio_bytes:
                    await send_voice_audio_message(remote_jid, audio_bytes)

                else:
                    await send_text_message(remote_jid, ai_response)

            else:
                await send_text_message(remote_jid, ai_response)

            await save_message(remote_jid, ai_response, sender="ia")

            # [NPS 2.1] Capturar resposta numérica de NPS se o paciente respondeu com nota de 0-10

            import re as _re

            nps_match = _re.fullmatch(r"\s*([0-9]|10)\s*", text.strip())

            if nps_match:
                try:
                    nps_score = int(nps_match.group(1))
                    from app.services.db_service import record_nps_score
                    
                    success = await record_nps_score(remote_jid, nps_score)
                    if success:
                        logger.info(f"NPS registrado: {nps_score}/10 para {remote_jid[:6]}****")
                except Exception as _e:
                    logger.warning(f"Aviso ao capturar NPS: {_e}")

            from app.api.endpoints.chats import manager

            await manager.broadcast("update")

        except Exception as e:
            print(f">>> [ERROR] Falha ao processar e responder: {e}", flush=True)


async def process_message(data: dict):
    """Extrai os dados da mensagem do payload Ghosthub e aciona o process_and_respond"""

    event_type = data.get("event", "")
    if not event_type:
        return

    event_type_upper = event_type.upper()

    if event_type_upper not in ["MESSAGES.UPSERT", "MESSAGES_UPSERT", "MESSAGE"]:
        return

    try:
        from_me = False
        remote_jid = ""
        push_name = "Cliente"
        text = ""
        is_audio = False

        if event_type_upper in ["MESSAGES.UPSERT", "MESSAGES_UPSERT"]:
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

            elif (
                "documentMessage" in message_obj
                or "documentWithCaptionMessage" in message_obj
                or message_type in ["documentMessage", "documentWithCaptionMessage"]
            ):
                doc_obj = (
                    message_obj.get("documentMessage")
                    or message_obj.get("documentWithCaptionMessage", {})
                    .get("message", {})
                    .get("documentMessage")
                    or message_obj
                )
                from app.services.media_handler import process_document_message
                text = await process_document_message(remote_jid, doc_obj)

            elif "imageMessage" in message_obj:
                img_data = message_obj.get("imageMessage", {})
                msg_id = data.get("id") or data.get("key", {}).get("id") or ""
                from app.services.media_handler import process_image_message
                text = await process_image_message(remote_jid, img_data, msg_id)

            elif "audioMessage" in message_obj or "pttMessage" in message_obj:
                is_audio = True
                audio_data = (
                    message_obj.get("audioMessage") or message_obj.get("pttMessage") or message_obj
                )
                msg_id = data.get("id") or data.get("key", {}).get("id") or ""
                from app.services.media_handler import process_audio_message
                text = await process_audio_message(audio_data, data, msg_id, remote_jid)

        if from_me:
            return

        # Se for áudio e a transcrição falhou (ex: quota Whisper esgotada ou ruído inaudível), acolhe o paciente

        if is_audio and not text:
            fallback_audio_msg = "Olá! Recebi seu áudio, mas no momento não consegui ouvir com total clareza. Você poderia enviar sua dúvida ou solicitação por mensagem de texto, por favor?"
            await send_text_message(remote_jid, fallback_audio_msg)

            await save_message(remote_jid, fallback_audio_msg, sender="ia")

            return

        if not text or not remote_jid:
            return

        if "status@broadcast" in remote_jid:
            return

        # [SEGURANÇA] Trava estrita contra DDoS Semântico e Token Flooding (Max 1.500 caracteres)

        if len(text) > 1500:
            logger.warning(
                f"Mensagem de {remote_jid} excedeu 1.500 caracteres ({len(text)}). Truncando com segurança."
            )

            text = text[:1500]

        logger.info(
            f"Processando Mensagem do paciente terminada em ...{remote_jid[-4:]} | Tamanho do texto: {len(text)} caracteres"
        )

        await process_and_respond(remote_jid, text, push_name, is_audio=is_audio)

    except Exception as e:
        print(f"Error processing webhook msg: {e}", flush=True)
