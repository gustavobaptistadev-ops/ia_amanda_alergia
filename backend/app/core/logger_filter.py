import logging
import re

CPF_REGEX = re.compile(r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b')
SECRET_REGEX = re.compile(r'(sk-[a-zA-Z0-9_\-]{20,}|Bearer\s+[a-zA-Z0-9_\-\.]+)', re.IGNORECASE)

class PIIMaskingFilter(logging.Filter):
    """
    Filtro de Logging nível Bancário/LGPD:
    Ofusca automaticamente CPFs e chaves de API secretas antes que sejam gravados no stdout/logs.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            # Mascara CPF -> ***.***.123-**
            record.msg = CPF_REGEX.sub(lambda m: f"***.***.{m.group(0)[-6:-3] if len(m.group(0))>=6 else '***'}-**", record.msg)
            # Mascara Segredos/Chaves
            record.msg = SECRET_REGEX.sub(r"[SECRET_REDACTED]", record.msg)
        return True
