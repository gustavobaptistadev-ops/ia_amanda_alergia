import logging
import re

CPF_REGEX = re.compile(r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b')
SECRET_REGEX = re.compile(r'(sk-[a-zA-Z0-9_\-]{20,}|Bearer\s+[a-zA-Z0-9_\-\.]+)', re.IGNORECASE)
TOKEN_QUERY_REGEX = re.compile(
    r'([?&](?:access_token|token|apikey|api_key|secret)=)[^&\s]+',
    re.IGNORECASE,
)
PHONE_REGEX = re.compile(r'(?<!\d)(?:55)?\d{10,13}(?!\d)')


def _mask_log_value(value):
    if not isinstance(value, str):
        return value
    value = CPF_REGEX.sub(
        lambda match: f"***.***.{match.group(0)[-6:-3] if len(match.group(0)) >= 6 else '***'}-**",
        value,
    )
    value = SECRET_REGEX.sub("[SECRET_REDACTED]", value)
    value = TOKEN_QUERY_REGEX.sub(r"\1[SECRET_REDACTED]", value)
    return PHONE_REGEX.sub("[PHONE_REDACTED]", value)

class PIIMaskingFilter(logging.Filter):
    """
    Filtro de Logging nível Bancário/LGPD:
    Ofusca automaticamente CPFs e chaves de API secretas antes que sejam gravados no stdout/logs.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _mask_log_value(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(_mask_log_value(value) for value in record.args)
        elif isinstance(record.args, dict):
            record.args = {
                key: _mask_log_value(value)
                for key, value in record.args.items()
            }
        return True
