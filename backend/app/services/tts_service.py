import logging
import os

from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)
openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def generate_speech_audio(text: str, voice: str = "nova") -> bytes:
    """
    Converte texto em áudio humanizado acolhedor usando OpenAI TTS (tts-1).
    Vozes recomendadas para saúde/recepção: 'nova' (feminina calorosa), 'shimmer' ou 'alloy'.
    """
    if not text or not text.strip():
        return None

    try:
        logger.info(f"Gerando áudio TTS ({len(text)} caracteres, voz '{voice}')...")
        response = await openai_client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text,
            response_format="opus",  # Formato nativo e leve para WhatsApp
        )
        audio_bytes = response.content
        logger.info(f"Áudio TTS gerado com sucesso ({len(audio_bytes)} bytes).")
        return audio_bytes
    except Exception as e:
        logger.error(f"Erro ao gerar áudio TTS: {e}")
        return None
