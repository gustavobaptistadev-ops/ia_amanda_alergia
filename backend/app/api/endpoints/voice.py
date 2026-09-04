from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
import json
import logging
from app.services.voice.stream_manager import StreamManager

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/twiml")
async def twilio_webhook(request: Request):
    """
    Endpoint inicial chamado pelo Twilio quando o paciente liga para a clínica.
    Retorna o TwiML instruindo o Twilio a abrir um WebSocket Bidirecional para a rota /stream.
    """
    host = request.headers.get("host", "")
    # Em produção, o host será o domínio ngrok ou o domínio real da clínica.
    # Precisamos garantir que seja wss:// se for HTTPS
    scheme = "wss" if "localhost" not in host and "127.0.0.1" not in host else "ws"
    
    ws_url = f"{scheme}://{host}/api/v1/voice/stream"
    
    twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{ws_url}" />
    </Connect>
</Response>"""

    return Response(content=twiml_response, media_type="application/xml")

@router.websocket("/stream")
async def voice_stream(websocket: WebSocket):
    """
    Endpoint WebSocket bidirecional para streaming de áudio (STT -> LLM -> TTS).
    O Twilio enviará pacotes de mídia em formato G.711 mu-law 8kHz.
    """
    await websocket.accept()
    stream_manager = StreamManager(websocket)
    
    try:
        await stream_manager.start()
        
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            
            if data['event'] == 'connected':
                logger.info("Twilio Stream connected")
            elif data['event'] == 'start':
                stream_sid = data['start']['streamSid']
                logger.info(f"Twilio Stream Started. SID: {stream_sid}")
                stream_manager.set_stream_sid(stream_sid)
            elif data['event'] == 'media':
                # payload é o áudio mu-law encodado em base64
                payload = data['media']['payload']
                await stream_manager.process_incoming_audio(payload)
            elif data['event'] == 'stop':
                logger.info("Twilio Stream Stopped")
                break
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected by Twilio.")
    except Exception as e:
        logger.error(f"Erro no WebSocket do Voice Agent: {str(e)}", exc_info=True)
    finally:
        await stream_manager.stop()
