import os
import io
import logging
import httpx
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def transcribe_audio_from_base64_or_url(audio_bytes: bytes, filename: str = "audio.ogg") -> str:
    """
    Recebe os bytes de áudio (formato OGG/Opus do WhatsApp ou MP3/WAV)
    e envia para a API do OpenAI Whisper para transcrição em português.
    """
    if not audio_bytes:
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
        logger.info(f"Transcrição concluída: {text}")
        return text
    except Exception as e:
        logger.error(f"Erro ao transcrever áudio com Whisper: {e}")
        return ""

async def download_audio_from_url(url: str, headers: dict = None) -> bytes:
    """Baixa o arquivo de áudio de uma URL protegida ou pública."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.content
            logger.error(f"Falha ao baixar áudio. Status code: {resp.status_code}")
            return None
    except Exception as e:
        logger.error(f"Erro no download do áudio: {e}")
        return None
