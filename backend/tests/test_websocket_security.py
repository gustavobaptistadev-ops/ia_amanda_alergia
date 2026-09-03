from types import SimpleNamespace

from app.core.security import get_websocket_protocol_token


def _websocket_with_protocol(value: str):
    return SimpleNamespace(headers={"sec-websocket-protocol": value})


def test_websocket_recebe_token_pelo_protocolo_do_handshake():
    websocket = _websocket_with_protocol("bearer, header.payload.signature")

    assert get_websocket_protocol_token(websocket) == "header.payload.signature"


def test_websocket_rejeita_cabecalho_sem_protocolo_bearer():
    websocket = _websocket_with_protocol("chat, header.payload.signature")

    assert get_websocket_protocol_token(websocket) is None


def test_websocket_rejeita_token_ausente():
    websocket = _websocket_with_protocol("bearer")

    assert get_websocket_protocol_token(websocket) is None
