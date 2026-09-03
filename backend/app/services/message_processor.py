from app.services.evolution_api import remove_emojis, send_text_message
from app.core.orchestrator import process_user_message
from app.core.guardrails import validar_resposta
from app.services.db_service import save_message, get_or_create_contact
from app.core.limiter import check_phone_rate_limit
import logging

import asyncio

logger = logging.getLogger(__name__)

import os
import redis.asyncio as redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# Palavras-gatilho de emergência médica real (triagem clínica)
EMERGENCY_TRIGGERS = [
    "anafilaxia", "anafil", "não consigo respirar", "nao consigo respirar",
    "falta de ar grave", "sufocando", "sufoca", "glote", "angioedema",
    "reação alérgica grave", "reacao alergica grave", "choque alérgico",
    "internação de emergência", "emergência médica", "samu", "pronto socorro urgente",
    "meu filho não respira", "minha filha não respira", "dificuldade respiratória severa",
    "inchando a garganta", "inchando o rosto todo", "urticária com falta de ar"
]

EMERGENCY_RESPONSE = (
    "⚠️ Identifiquei que você pode estar passando por uma situação de urgência médica.\n\n"
    "Se for uma emergência imediata, ligue agora para o *SAMU 192* ou vá ao Pronto-Socorro mais próximo.\n\n"
    "Assim que você estiver seguro(a), vou estar aqui para agendar sua consulta de acompanhamento com nossos especialistas. Cuide-se! 🙏"
)

async def process_and_respond(remote_jid: str, text: str, push_name: str, is_audio: bool = False):
    """Executa a logica pesada de IA e envia a resposta de forma estritamente sequencial (lock distribuído via Redis)."""

    # [SEGURANÇA 1.1] Rate Limit por número de telefone — protege contra DDoS semântico
    is_rate_limited = await check_phone_rate_limit(remote_jid, max_per_minute=20)
    if is_rate_limited:
        logger.warning(f"Rate limit atingido para {remote_jid[:6]}****. Mensagem ignorada.")
        await send_text_message(remote_jid, "Estou recebendo muitas mensagens em seguida. Aguarde um momento e tente novamente!")
        return

    # [SEGURANÇA 2.3] Triagem de Emergência — detecta urgência real ANTES do processamento da IA
    text_lower = text.lower() if text else ""
    is_emergency = any(trigger in text_lower for trigger in EMERGENCY_TRIGGERS)
    if is_emergency:
        logger.warning(f"TRIAGEM DE EMERGÊNCIA acionada para {remote_jid[:6]}****. Enviando resposta de segurança imediata.")
        await send_text_message(remote_jid, EMERGENCY_RESPONSE)
        await save_message(remote_jid, text, sender='paciente', name=push_name)
        await save_message(remote_jid, remove_emojis(EMERGENCY_RESPONSE), sender='ia')
        from app.models.chat import SystemLog
        from app.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            session.add(SystemLog(
                category="triagem_emergencia",
                level="ALERTA",
                title=f"Emergência detectada: {push_name or remote_jid[:6]}****",
                detail=f"Gatilho: '{text[:80]}' | JID: {remote_jid[:6]}****"
            ))
            await session.commit()
        return


    # Lock distribuído (timeout: liberta a trava se o worker morrer; blocking_timeout: aguarda até 2 mins por outra msg terminar)
    async with redis_client.lock(f"lock:patient:{remote_jid}", timeout=180, blocking_timeout=120):
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

            try:
                ai_response = await process_user_message(thread_id=remote_jid, message=text)
            except Exception as e:
                logger.error(f"Erro ao processar mensagem no LLM para {remote_jid}: {e}")
                ai_response = "Nosso sistema está passando por uma instabilidade momentânea. Um de nossos atendentes humanos já foi notificado e falará com você em breve."
            
            ai_response = remove_emojis(ai_response)
            is_safe = validar_resposta(ai_response)
            
            if not is_safe:
                # Se for bloqueio real de segurança (prescrição ou jailbreak), responde com prudência médica
                ai_response = "Por diretrizes do Conselho de Medicina e segurança clínica, prescrições de remédios e orientações de posologia são realizadas exclusivamente pelo médico durante a sua consulta. Posso te ajudar a agendar um horário com nossos especialistas?"

            if "⚠️ Identifiquei que você pode estar passando por uma situação de urgência" in ai_response or "[TRANSFERIR_HUMANO]" in ai_response:
                logger.warning(f"Escalando para atendimento humano: {remote_jid}")
                from app.database import AsyncSessionLocal
                from app.models.chat import Contact
                from sqlalchemy.future import select
                
                # Remover a tag secreta antes de enviar ao paciente
                ai_response = ai_response.replace("[TRANSFERIR_HUMANO]", "").strip()
                
                async with AsyncSessionLocal() as session:
                    res = await session.execute(select(Contact).where(Contact.phone_number == remote_jid))
                    c = res.scalars().first()
                    if c:
                        c.bot_active = False
                        c.stage = "atendimento_humano"
                        await session.commit()
                
                # Disparar alerta visual/sonoro via WebSocket
                await manager.broadcast(f"urgency:{remote_jid}")

            # [MULTIMODAL] Se o paciente mandou áudio e a opção de voz estiver ligada, responder com áudio TTS
            from app.api.endpoints.settings import load_config
            cfg = load_config()
            voice_enabled = cfg.get("voice_reply_enabled", False)

            if is_audio and voice_enabled:
                from app.services.tts_service import generate_speech_audio
                from app.services.evolution_api import send_voice_audio_message
                voice_name = cfg.get("voice_name", "nova")
                audio_bytes = await generate_speech_audio(ai_response, voice=voice_name)
                if audio_bytes:
                    await send_voice_audio_message(remote_jid, audio_bytes)
                else:
                    await send_text_message(remote_jid, ai_response)
            else:
                await send_text_message(remote_jid, ai_response)

            await save_message(remote_jid, ai_response, sender='ia')

            # [NPS 2.1] Capturar resposta numérica de NPS se o paciente respondeu com nota de 0-10
            import re as _re
            nps_match = _re.fullmatch(r"\s*([0-9]|10)\s*", text.strip())
            if nps_match:
                try:
                    nps_score = int(nps_match.group(1))
                    from app.database import AsyncSessionLocal as _ASL
                    from app.models.chat import Appointment as _Appt, Contact as _Cont
                    from sqlalchemy.future import select as _select
                    async with _ASL() as _session:
                        _clean = _re.sub(r"\D", "", remote_jid)
                        _stmt = _select(_Cont).where(_Cont.phone_number.contains(_clean[-8:] if len(_clean) >= 8 else _clean))
                        _res = await _session.execute(_stmt)
                        _contact = _res.scalars().first()
                        if _contact:
                            _stmt_apt = _select(_Appt).where(
                                _Appt.contact_id == _contact.id,
                                _Appt.nps_sent == True,
                                _Appt.nps_score == None
                            ).order_by(_Appt.created_at.desc()).limit(1)
                            _res_apt = await _session.execute(_stmt_apt)
                            _apt = _res_apt.scalars().first()
                            if _apt:
                                _apt.nps_score = nps_score
                                await _session.commit()
                                logger.info(f"NPS registrado: {nps_score}/10 para {remote_jid[:6]}****")
                except Exception as _e:
                    logger.warning(f"Aviso ao capturar NPS: {_e}")
            
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
        is_audio = False

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
            elif "documentMessage" in message_obj or "documentWithCaptionMessage" in message_obj or message_type in ["documentMessage", "documentWithCaptionMessage"]:
                doc_obj = message_obj.get("documentMessage") or message_obj.get("documentWithCaptionMessage", {}).get("message", {}).get("documentMessage") or message_obj
                caption = doc_obj.get("caption", "")
                filename = doc_obj.get("fileName") or doc_obj.get("filename") or "documento.pdf"
                logger.info(f"Detectado documento enviado pelo paciente (upsert): {filename}. Processando OCR de PDF/Carteirinha...")
                from app.services.vision_service import process_health_card_document
                from app.services.audio_service import download_audio_from_url, decrypt_whatsapp_media
                import base64

                raw_doc = None
                b64_val = doc_obj.get("base64") or doc_obj.get("Base64") or doc_obj.get("media") or ""
                media_key = doc_obj.get("mediaKey")
                media_url = doc_obj.get("url") or doc_obj.get("URL") or ""

                if b64_val:
                    if "," in b64_val:
                        b64_val = b64_val.split(",")[1]
                    raw_doc = base64.b64decode(b64_val)
                elif media_url and media_key:
                    enc_bytes = await download_audio_from_url(media_url)
                    if enc_bytes:
                        raw_doc = decrypt_whatsapp_media(enc_bytes, media_key, media_type="document")
                elif media_url and not ".enc" in media_url:
                    raw_doc = await download_audio_from_url(media_url)

                if raw_doc:
                    card_data = await process_health_card_document(raw_doc, filename=filename)
                    if card_data.get("is_health_card"):
                        from app.database import AsyncSessionLocal
                        from app.models.chat import Contact
                        from sqlalchemy.future import select
                        async with AsyncSessionLocal() as session:
                            res = await session.execute(select(Contact).where(Contact.phone_number == remote_jid))
                            c = res.scalars().first()
                            if c:
                                c.insurance_operator = card_data.get("operator")
                                c.insurance_card_number = card_data.get("card_number")
                                c.insurance_plan_name = card_data.get("plan_name")
                                c.insurance_coverage = card_data.get("coverage_area")
                                c.insurance_accommodation = card_data.get("accommodation")
                                if card_data.get("patient_name") and not c.name:
                                    c.name = card_data.get("patient_name")
                                await session.commit()

                        text = f"[O paciente enviou o PDF/comprovante da sua carteirinha de convênio ({card_data.get('operator')}). DADOS EXTRAÍDOS PELA VISÃO COMPUTACIONAL: Operadora: {card_data.get('operator')}, Matrícula: {card_data.get('card_number')}, Plano: {card_data.get('plan_name')}, Acomodação: {card_data.get('accommodation')}, Abrangência: {card_data.get('coverage_area')}, Titular: {card_data.get('patient_name')}]. {caption}"
                    else:
                        text = f"[O paciente enviou um documento PDF ({filename}). Resumo do conteúdo: {card_data.get('summary_for_chat')}]. {caption}"
                else:
                    text = caption or f"[Documento PDF {filename} enviado pelo paciente]"
            elif "imageMessage" in message_obj:
                caption = message_obj["imageMessage"].get("caption", "")
                logger.info("Detectada imagem enviada pelo paciente. Acionando módulo Vision OCR de Carteirinhas...")
                from app.services.vision_service import process_health_card_document
                from app.services.audio_service import download_audio_from_url, decrypt_whatsapp_media
                import base64
                
                img_data = message_obj.get("imageMessage", {})
                raw_img = None
                b64_val = img_data.get("base64") or img_data.get("Base64") or img_data.get("media") or ""
                media_key = img_data.get("mediaKey")
                media_url = img_data.get("url") or img_data.get("URL") or ""

                if b64_val:
                    if "," in b64_val:
                        b64_val = b64_val.split(",")[1]
                    raw_img = base64.b64decode(b64_val)
                elif media_url and media_key:
                    enc_bytes = await download_audio_from_url(media_url)
                    if enc_bytes:
                        raw_img = decrypt_whatsapp_media(enc_bytes, media_key, media_type="image")
                elif media_url and not ".enc" in media_url:
                    raw_img = await download_audio_from_url(media_url)

                if raw_img:
                    card_data = await process_health_card_document(raw_img)
                    if card_data.get("is_health_card"):
                        # Atualiza dados do contato no banco relacional
                        from app.database import AsyncSessionLocal
                        from app.models.chat import Contact
                        from sqlalchemy.future import select
                        async with AsyncSessionLocal() as session:
                            res = await session.execute(select(Contact).where(Contact.phone_number == remote_jid))
                            c = res.scalars().first()
                            if c:
                                c.insurance_operator = card_data.get("operator")
                                c.insurance_card_number = card_data.get("card_number")
                                c.insurance_plan_name = card_data.get("plan_name")
                                c.insurance_coverage = card_data.get("coverage_area")
                                c.insurance_accommodation = card_data.get("accommodation")
                                if card_data.get("patient_name") and not c.name:
                                    c.name = card_data.get("patient_name")
                                await session.commit()

                        text = f"[O paciente enviou a foto da sua carteirinha de convênio. DADOS EXTRAÍDOS PELA VISÃO COMPUTACIONAL: Operadora: {card_data.get('operator')}, Matrícula: {card_data.get('card_number')}, Plano: {card_data.get('plan_name')}, Acomodação: {card_data.get('accommodation')}, Abrangência: {card_data.get('coverage_area')}, Titular: {card_data.get('patient_name')}]. {caption}"
                    else:
                        text = f"[O paciente enviou uma imagem/documento. Resumo visual: {card_data.get('summary_for_chat')}]. {caption}"
                else:
                    text = caption or "[Foto enviada pelo paciente]"
            elif "audioMessage" in message_obj or "pttMessage" in message_obj or message_type in ["audioMessage", "pttMessage"]:
                is_audio = True
                logger.info("Detectada mensagem de áudio (messages.upsert). Iniciando transcrição com Whisper...")
                from app.services.audio_service import transcribe_audio_from_base64_or_url, download_audio_from_url, decrypt_whatsapp_media
                import base64
                
                audio_data = message_obj.get("audioMessage") or message_obj.get("pttMessage") or message_obj
                raw_audio = None
                
                if isinstance(audio_data, dict):
                    b64_val = audio_data.get("base64") or audio_data.get("Base64") or audio_data.get("media") or ""
                    media_key = audio_data.get("mediaKey")
                    media_url = audio_data.get("url") or audio_data.get("URL") or ""

                    if b64_val:
                        if "," in b64_val:
                            b64_val = b64_val.split(",")[1]
                        raw_audio = base64.b64decode(b64_val)
                    elif media_url and media_key:
                        enc_bytes = await download_audio_from_url(media_url)
                        if enc_bytes:
                            raw_audio = decrypt_whatsapp_media(enc_bytes, media_key, media_type="audio")
                    elif media_url and not ".enc" in media_url:
                        raw_audio = await download_audio_from_url(media_url)
                elif isinstance(audio_data, str) and (audio_data.startswith("http") or audio_data.startswith("data:audio")):
                    raw_audio = await download_audio_from_url(audio_data)

                if raw_audio:
                    text = await transcribe_audio_from_base64_or_url(raw_audio)
                else:
                    logger.warning(f"Não foi possível obter os bytes do áudio no payload (upsert): {audio_data}")

        elif event_type == "Message":
            info = data.get("data", {}).get("Info", {})
            message_obj = data.get("data", {}).get("Message", {})
            message_type = info.get("MediaType", "")
            from_me = info.get("IsFromMe", False)
            
            # Suporte a AddressingMode: lid / jid padrão da Evolution
            remote_jid = info.get("Chat", "") or info.get("Sender", "") or info.get("SenderAlt", "") or info.get("RemoteJid", "")
            if not remote_jid and isinstance(data.get("data"), dict):
                remote_jid = data.get("data", {}).get("key", {}).get("remoteJid", "")
                
            push_name = info.get("PushName", "") or info.get("pushName", "Cliente")
            if info.get("IsGroup", False):
                 return
            if "conversation" in message_obj:
                text = message_obj["conversation"]
            elif "extendedTextMessage" in message_obj:
                text = message_obj["extendedTextMessage"].get("text", "")
            elif isinstance(message_obj, str):
                text = message_obj
            elif "documentMessage" in message_obj or "documentWithCaptionMessage" in message_obj or message_type in ["documentMessage", "documentWithCaptionMessage"]:
                doc_obj = message_obj.get("documentMessage") or message_obj.get("documentWithCaptionMessage", {}).get("message", {}).get("documentMessage") or message_obj
                caption = doc_obj.get("caption", "")
                filename = doc_obj.get("fileName") or doc_obj.get("filename") or "documento.pdf"
                logger.info(f"Detectado documento enviado pelo paciente: {filename}. Processando OCR de PDF/Carteirinha...")
                from app.services.vision_service import process_health_card_document
                from app.services.audio_service import download_audio_from_url, decrypt_whatsapp_media
                import base64

                raw_doc = None
                b64_val = doc_obj.get("base64") or doc_obj.get("Base64") or doc_obj.get("media") or ""
                media_key = doc_obj.get("mediaKey")
                media_url = doc_obj.get("url") or doc_obj.get("URL") or ""

                if b64_val:
                    if "," in b64_val:
                        b64_val = b64_val.split(",")[1]
                    raw_doc = base64.b64decode(b64_val)
                elif media_url and media_key:
                    enc_bytes = await download_audio_from_url(media_url)
                    if enc_bytes:
                        raw_doc = decrypt_whatsapp_media(enc_bytes, media_key, media_type="document")
                elif media_url and not ".enc" in media_url:
                    raw_doc = await download_audio_from_url(media_url)

                if raw_doc:
                    card_data = await process_health_card_document(raw_doc, filename=filename)
                    if card_data.get("is_health_card"):
                        from app.database import AsyncSessionLocal
                        from app.models.chat import Contact
                        from sqlalchemy.future import select
                        async with AsyncSessionLocal() as session:
                            res = await session.execute(select(Contact).where(Contact.phone_number == remote_jid))
                            c = res.scalars().first()
                            if c:
                                c.insurance_operator = card_data.get("operator")
                                c.insurance_card_number = card_data.get("card_number")
                                c.insurance_plan_name = card_data.get("plan_name")
                                c.insurance_coverage = card_data.get("coverage_area")
                                c.insurance_accommodation = card_data.get("accommodation")
                                if card_data.get("patient_name") and not c.name:
                                    c.name = card_data.get("patient_name")
                                await session.commit()

                        text = f"[O paciente enviou o PDF/comprovante da sua carteirinha de convênio ({card_data.get('operator')}). DADOS EXTRAÍDOS PELA VISÃO COMPUTACIONAL: Operadora: {card_data.get('operator')}, Matrícula: {card_data.get('card_number')}, Plano: {card_data.get('plan_name')}, Acomodação: {card_data.get('accommodation')}, Abrangência: {card_data.get('coverage_area')}, Titular: {card_data.get('patient_name')}]. {caption}"
                    else:
                        text = f"[O paciente enviou um documento PDF ({filename}). Resumo do conteúdo: {card_data.get('summary_for_chat')}]. {caption}"
                else:
                    text = caption or f"[Documento PDF {filename} enviado pelo paciente]"
            elif "imageMessage" in message_obj:
                caption = message_obj["imageMessage"].get("caption", "")
                logger.info("Detectada imagem enviada pelo paciente (Message). Acionando módulo Vision OCR de Carteirinhas...")
                from app.services.vision_service import process_health_card_document
                from app.services.audio_service import download_audio_from_url, decrypt_whatsapp_media
                import base64
                
                img_data = message_obj.get("imageMessage", {})
                raw_img = None
                b64_val = img_data.get("base64") or img_data.get("Base64") or img_data.get("media") or ""
                media_key = img_data.get("mediaKey")
                media_url = img_data.get("url") or img_data.get("URL") or ""

                if b64_val:
                    if "," in b64_val:
                        b64_val = b64_val.split(",")[1]
                    raw_img = base64.b64decode(b64_val)
                elif media_url and media_key:
                    enc_bytes = await download_audio_from_url(media_url)
                    if enc_bytes:
                        raw_img = decrypt_whatsapp_media(enc_bytes, media_key, media_type="image")
                elif media_url and not ".enc" in media_url:
                    raw_img = await download_audio_from_url(media_url)

                if not raw_img:
                    msg_id = info.get("Id") or info.get("ID") or info.get("id") or ""
                    if msg_id:
                        from app.services.evolution_api import get_base64_from_media
                        raw_img = await get_base64_from_media(msg_id, remote_jid)

                if raw_img:
                    card_data = await process_health_card_document(raw_img)
                    if card_data.get("is_health_card"):
                        from app.database import AsyncSessionLocal
                        from app.models.chat import Contact
                        from sqlalchemy.future import select
                        async with AsyncSessionLocal() as session:
                            res = await session.execute(select(Contact).where(Contact.phone_number == remote_jid))
                            c = res.scalars().first()
                            if c:
                                c.insurance_operator = card_data.get("operator")
                                c.insurance_card_number = card_data.get("card_number")
                                c.insurance_plan_name = card_data.get("plan_name")
                                c.insurance_coverage = card_data.get("coverage_area")
                                c.insurance_accommodation = card_data.get("accommodation")
                                if card_data.get("patient_name") and not c.name:
                                    c.name = card_data.get("patient_name")
                                await session.commit()

                        text = f"[O paciente enviou a foto da sua carteirinha de convênio. DADOS EXTRAÍDOS PELA VISÃO COMPUTACIONAL: Operadora: {card_data.get('operator')}, Matrícula: {card_data.get('card_number')}, Plano: {card_data.get('plan_name')}, Acomodação: {card_data.get('accommodation')}, Abrangência: {card_data.get('coverage_area')}, Titular: {card_data.get('patient_name')}]. {caption}"
                    else:
                        text = f"[O paciente enviou uma imagem/documento. Resumo visual: {card_data.get('summary_for_chat')}]. {caption}"
                else:
                    text = caption or "[Foto enviada pelo paciente]"
            elif "audioMessage" in msg_obj or "pttMessage" in msg_obj:
                is_audio = True
                logger.info("Detectada mensagem de áudio (Message). Iniciando transcrição com Whisper...")
                from app.services.audio_service import transcribe_audio_from_base64_or_url, download_audio_from_url
                import base64
                
                audio_data = msg_obj.get("audioMessage") or msg_obj.get("pttMessage") or msg_obj
                raw_audio = None
                
                # 1. Primeiro checa se o payload já trouxe o base64 descompactado
                b64_val = audio_data.get("base64") or audio_data.get("Base64") or audio_data.get("media") if isinstance(audio_data, dict) else ""
                if b64_val:
                    if "," in b64_val:
                        b64_val = b64_val.split(",")[1]
                    raw_audio = base64.b64decode(b64_val)

                # 2. Descriptografia Nativa WhatsApp (E2EE WhatsApp Media Decryption)
                # Se temos a URL do arquivo .enc e a chave 'mediaKey', fazemos o download e descriptografamos via HKDF/AES-CBC
                if not raw_audio and isinstance(audio_data, dict):
                    media_key = audio_data.get("mediaKey")
                    media_url = audio_data.get("URL") or audio_data.get("url") or ""
                    
                    if media_url and media_key:
                        from app.services.audio_service import decrypt_whatsapp_media
                        logger.info("Baixando arquivo .enc do WhatsApp e descriptografando via chave E2EE (mediaKey)...")
                        enc_bytes = await download_audio_from_url(media_url)
                        if enc_bytes:
                            raw_audio = decrypt_whatsapp_media(enc_bytes, media_key, media_type="audio")

                # 3. Fallback: Se for URL pública direta (não-criptografada)
                if not raw_audio and isinstance(audio_data, dict):
                    url_val = audio_data.get("URL") or audio_data.get("url") or audio_data.get("file") or ""
                    if url_val and not ".enc" in url_val:
                        raw_audio = await download_audio_from_url(url_val)

                # 4. Fallback final via API da instância (Message ID)
                if not raw_audio:
                    msg_id = info.get("Id") or info.get("ID") or info.get("id") or ""
                    if msg_id:
                        from app.services.evolution_api import get_base64_from_media
                        raw_audio = await get_base64_from_media(msg_id, remote_jid)

                if raw_audio:
                    text = await transcribe_audio_from_base64_or_url(raw_audio)
                    if not text:
                        logger.warning(f"Transcrição do áudio retornou vazia para {remote_jid}.")
                else:
                    logger.warning(f"Não foi possível obter os bytes descriptografados do áudio: {audio_data}")

        if from_me:
             return
        
        # Se for áudio e a transcrição falhou (ex: quota Whisper esgotada ou ruído inaudível), acolhe o paciente
        if is_audio and not text:
             fallback_audio_msg = "🌻 Olá! Recebi seu áudio, mas no momento não consegui ouvir com total clareza. Você poderia me enviar sua dúvida ou solicitação por mensagem de texto, por favor? Assim já consigo te ajudar rapidinho!"
             await send_text_message(remote_jid, fallback_audio_msg)
             await save_message(remote_jid, fallback_audio_msg, sender='ia')
             return

        if not text or not remote_jid:
             return
        if "status@broadcast" in remote_jid:
             return

        # [SEGURANÇA] Trava estrita contra DDoS Semântico e Token Flooding (Max 1.500 caracteres)
        if len(text) > 1500:
            logger.warning(f"Mensagem de {remote_jid} excedeu 1.500 caracteres ({len(text)}). Truncando com segurança.")
            text = text[:1500]

        logger.info(f"Processando Mensagem do paciente terminada em ...{remote_jid[-4:]} | Tamanho do texto: {len(text)} caracteres")
        await process_and_respond(remote_jid, text, push_name, is_audio=is_audio)
        
    except Exception as e:
        print(f"Error processing webhook msg: {e}", flush=True)
