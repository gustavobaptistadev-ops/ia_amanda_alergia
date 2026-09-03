import logging

from app.core.logger_filter import PIIMaskingFilter


def test_filtro_remove_access_token_dos_argumentos_do_uvicorn():
    token = "header.payload.signature"
    record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='%s - "WebSocket %s" [accepted]',
        args=("100.64.0.1:1234", f"/api/v1/chats/ws?access_token={token}"),
        exc_info=None,
    )

    assert PIIMaskingFilter().filter(record) is True
    rendered = record.getMessage()

    assert token not in rendered
    assert "access_token=[SECRET_REDACTED]" in rendered


def test_filtro_preserva_argumentos_nao_textuais():
    record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="status=%d",
        args=(200,),
        exc_info=None,
    )

    PIIMaskingFilter().filter(record)

    assert record.getMessage() == "status=200"
