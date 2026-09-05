import logging

from fastapi import WebSocket

# Mocks temporários até integrarmos Deepgram e ElevenLabs
# from app.services.voice.stt_service import STTService
# from app.services.voice.tts_service import TTSService

logger = logging.getLogger(__name__)


class StreamManager:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.stream_sid = None
        # self.stt = STTService()
        # self.tts = TTSService(self.send_audio_to_twilio)
        self.is_running = False

    def set_stream_sid(self, stream_sid: str):
        self.stream_sid = stream_sid

    async def start(self):
        self.is_running = True
        logger.info("StreamManager started")
        # await self.stt.start()
        # await self.tts.start()

    async def stop(self):
        self.is_running = False
        logger.info("StreamManager stopped")
        # await self.stt.stop()
        # await self.tts.stop()

    async def process_incoming_audio(self, payload_base64: str):
        """
        Recebe o payload G.711 mu-law do Twilio e envia para o STT (Deepgram).
        """
        pass
        # await self.stt.send_audio(payload_base64)

        # Simulação temporária:
        # Quando tivermos a transcrição real, passaremos para o LLM
        # e a resposta do LLM irá para o TTS.

    async def send_audio_to_twilio(self, audio_payload_base64: str):
        """
        Callback usado pelo TTSService para enviar o áudio sintetizado de volta para a ligação.
        """
        if not self.stream_sid or not self.is_running:
            return

        message = {
            "event": "media",
            "streamSid": self.stream_sid,
            "media": {"payload": audio_payload_base64},
        }
        await self.websocket.send_json(message)
