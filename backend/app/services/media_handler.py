import logging
import base64
from app.services.audio_service import decrypt_whatsapp_media, download_audio_from_url, transcribe_audio_from_base64_or_url
from app.services.vision_service import process_health_card_document
from app.services.db_service import update_contact_insurance_info


logger = logging.getLogger(__name__)


async def process_document_message(remote_jid, doc_obj) -> str:
    caption = doc_obj.get("caption", "")
    filename = doc_obj.get("fileName") or doc_obj.get("filename") or "documento.pdf"
    logger.info(f"Processando documento: {filename}")
    
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
    elif media_url and ".enc" not in media_url:
        raw_doc = await download_audio_from_url(media_url)

    if raw_doc:
        card_data = await process_health_card_document(raw_doc, filename=filename)
        if card_data.get("is_health_card"):
            await update_contact_insurance_info(remote_jid, card_data)
            return f"[O paciente enviou o PDF/comprovante da sua carteirinha de convÃªnio ({card_data.get('operator')}). DADOS EXTRAÃDOS PELA VISÃƒO COMPUTACIONAL: Operadora: {card_data.get('operator')}, MatrÃ­cula: {card_data.get('card_number')}, Plano: {card_data.get('plan_name')}, AcomodaÃ§Ã£o: {card_data.get('accommodation')}, AbrangÃªncia: {card_data.get('coverage_area')}, Titular: {card_data.get('patient_name')}]. {caption}"
        return f"[O paciente enviou um documento PDF ({filename}). Resumo do conteÃºdo: {card_data.get('summary_for_chat')}]. {caption}"
    
    return caption or f"[Documento PDF {filename} enviado pelo paciente]"



async def process_image_message(remote_jid, img_data, msg_id="") -> str:
    caption = img_data.get("caption", "")
    logger.info("Processando imagem enviada...")
    
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
    elif media_url and ".enc" not in media_url:
        raw_img = await download_audio_from_url(media_url)

    if not raw_img and msg_id:
        from app.services.evolution_api import get_base64_from_media
        raw_img = await get_base64_from_media(msg_id, remote_jid)

    if raw_img:
        card_data = await process_health_card_document(raw_img)
        if card_data.get("is_health_card"):
            await update_contact_insurance_info(remote_jid, card_data)
            return f"[O paciente enviou a foto da sua carteirinha de convÃªnio. DADOS EXTRAÃDOS PELA VISÃƒO COMPUTACIONAL: Operadora: {card_data.get('operator')}, MatrÃ­cula: {card_data.get('card_number')}, Plano: {card_data.get('plan_name')}, AcomodaÃ§Ã£o: {card_data.get('accommodation')}, AbrangÃªncia: {card_data.get('coverage_area')}, Titular: {card_data.get('patient_name')}]. {caption}"
        return f"[O paciente enviou uma imagem/documento. Resumo visual: {card_data.get('summary_for_chat')}]. {caption}"
    
    return caption or "[Foto enviada pelo paciente]"



async def process_audio_message(audio_data, data, msg_id="", remote_jid="") -> str:
    logger.info("Processando Ã¡udio (Whisper)...")
    raw_audio = None

    if isinstance(audio_data, dict):
        b64_val = (
            data.get("base64")
            or audio_data.get("base64")
            or audio_data.get("Base64")
            or audio_data.get("media")
            or ""
        )
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
        elif media_url and ".enc" not in media_url:
            raw_audio = await download_audio_from_url(media_url)

    elif isinstance(audio_data, str) and (audio_data.startswith("http") or audio_data.startswith("data:audio")):
        raw_audio = await download_audio_from_url(audio_data)

    if not raw_audio and msg_id and remote_jid:
        from app.services.evolution_api import get_base64_from_media
        raw_audio = await get_base64_from_media(msg_id, remote_jid, message_obj=data.get("data", {}))

    if raw_audio:
        return await transcribe_audio_from_base64_or_url(raw_audio)
    
    logger.warning("NÃ£o foi possÃ­vel extrair os bytes do Ã¡udio.")
    return "ERRO_RAW_AUDIO: bytes_none"
