import base64
import io
import logging
import os

import httpx
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


def decrypt_whatsapp_media(
    enc_bytes: bytes, media_key_b64: str, media_type: str = "audio"
) -> bytes:
    """
    Descriptografa arquivos de mídia (.enc) do WhatsApp usando a especificação oficial de E2EE:
    1. Derivação de chaves via HKDF SHA-256 com info 'WhatsApp Audio Keys'
    2. Validação de HMAC SHA-256
    3. Descriptografia AES-256-CBC
    """
    try:
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF

        media_key = base64.b64decode(media_key_b64)

        info_str = "WhatsApp Audio Keys".encode("latin-1")
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=112,
            salt=b"",
            info=info_str,
            backend=default_backend(),
        )
        key_stream = hkdf.derive(media_key)

        iv = key_stream[0:16]
        cipher_key = key_stream[16:48]
        mac_key = key_stream[48:80]

        # Os últimos 10 bytes do arquivo .enc são o MAC
        file_data = enc_bytes[:-10]
        file_mac = enc_bytes[-10:]

        # Descriptografia AES-CBC
        cipher = Cipher(
            algorithms.AES(cipher_key), modes.CBC(iv), backend=default_backend()
        )
        decryptor = cipher.decryptor()
        decrypted_padded = decryptor.update(file_data) + decryptor.finalize()

        # Remove PKCS7 padding
        pad_len = decrypted_padded[-1]
        if pad_len <= 16:
            decrypted_data = decrypted_padded[:-pad_len]
        else:
            decrypted_data = decrypted_padded

        logger.info(
            f"Áudio WhatsApp .enc descriptografado com sucesso! ({len(decrypted_data)} bytes Opus puro)."
        )
        return decrypted_data
    except Exception as e:
        logger.error(f"Erro na descriptografia HKDF/AES do áudio WhatsApp: {e}")
        return None


async def transcribe_audio_from_base64_or_url(
    audio_bytes: bytes, filename: str = "audio.ogg"
) -> str:
    """
    Recebe os bytes de áudio (formato OGG/Opus do WhatsApp, MP3 ou WAV)
    e envia para a API do OpenAI Whisper para transcrição em português.
    """
    if not audio_bytes or len(audio_bytes) < 100:
        logger.warning("Bytes de áudio vazios ou insuficientes para transcrição.")
        return ""

    try:
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = filename

        logger.info(
            f"Enviando {len(audio_bytes)} bytes de áudio para o Whisper-1 (filename={filename})..."
        )
        transcript = await openai_client.audio.transcriptions.create(
            model="whisper-1", file=audio_file, language="pt"
        )
        text = transcript.text.strip()
        logger.info(f"Transcrição de áudio concluída com sucesso: '{text}'")
        return text
    except Exception as e:
        logger.error(f"Erro ao transcrever áudio com Whisper: {e}")
        return ""


async def download_audio_from_url(url: str, headers: dict = None) -> bytes:
    """Baixa o arquivo de áudio de uma URL protegida ou pública."""
    if not url:
        return None
    try:
        if url.startswith("data:audio"):
            parts = url.split(",")
            if len(parts) > 1:
                return base64.b64decode(parts[1])

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                logger.info(f"Download do arquivo concluído ({len(resp.content)} bytes).")
                return resp.content
            logger.error(
                f"Falha ao baixar áudio de '{url}'. Status code: {resp.status_code}"
            )
            return None
    except Exception as e:
        logger.error(f"Erro no download do áudio ({url}): {e}")
        return None
