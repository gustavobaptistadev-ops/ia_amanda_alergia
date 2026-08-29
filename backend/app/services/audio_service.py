import os
import io
import logging
import httpx
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def transcribe_audio_from_base64_or_url(audio_bytes: bytes, filename: str = "audio.ogg") -> str:
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

        logger.info(f"Enviando {len(audio_bytes)} bytes de áudio para o Whisper-1...")
        transcript = await openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="pt"
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
        # Se for data:audio URL base64 embutida
        if url.startswith("data:audio"):
            import base64
            parts = url.split(",")
            if len(parts) > 1:
                return base64.b64decode(parts[1])
                
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                logger.info(f"Download do áudio concluído ({len(resp.content)} bytes).")
                return resp.content
            logger.error(f"Falha ao baixar áudio de '{url}'. Status code: {resp.status_code}")
            return None
    except Exception as e:
        logger.error(f"Erro no download do áudio ({url}): {e}")
        return None

