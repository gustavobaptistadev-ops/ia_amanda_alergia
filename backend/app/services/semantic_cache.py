import logging
import os
import hashlib
import json
import redis.asyncio as redis
from typing import Optional

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL_SECONDS = 60 * 60 * 24 * 7 # 7 dias de retenção

# Normalização de texto para chave de cache
DYNAMIC_CONVERSATION_TERMS = (
    "agendar", "consulta", "horario", "marcar", "cpf", "nascimento",
    "convenio", "particular", "plano", "remarcar", "cancelar",
    "segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo",
    "hoje", "amanha", "ontem",
)


def is_dynamic_conversation_message(user_message: str) -> bool:
    """Identifica dados que nunca podem receber uma resposta cacheada."""
    import re
    import unicodedata

    raw = (user_message or "").lower()
    normalized = unicodedata.normalize("NFKD", raw)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    if any(term in normalized for term in DYNAMIC_CONVERSATION_TERMS):
        return True
    if re.search(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b", normalized):
        return True
    if re.search(r"\b\d{1,2}(?::\d{2})?\s*h?\b", normalized):
        return True
    return bool(re.search(r"\b\d{8,}\b", normalized))


def generate_cache_key(text: str) -> str:
    """Gera uma chave determinística normalizada para perguntas frequentes."""
    import re, unicodedata
    clean = unicodedata.normalize("NFKD", text).lower().strip()
    clean = re.sub(r"[^\w\s]", "", clean)
    clean = re.sub(r"\s+", " ", clean)
    digest = hashlib.sha256(clean.encode("utf-8")).hexdigest()[:16]
    return f"semantic_cache:{digest}"

async def get_cached_response(user_message: str) -> Optional[str]:
    """Busca no Redis uma resposta em cache se a Feature Flag estiver ativada."""
    try:
        from app.api.endpoints.settings import load_config
        cfg = load_config()
        if not cfg.get("semantic_cache_enabled", True):
            return None

        # Não cachear mensagens com dados clínicos de agendamento ou números de CPF
        import re
        if re.search(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", user_message) or len(user_message.strip()) < 4:
            return None

        normalized_message = user_message.strip().lower()
        scheduling_terms = ("agendar", "consulta", "horário", "horario", "marcar", "cpf", "nascimento", "convênio", "convenio", "remarcar", "cancelar")
        if (is_dynamic_conversation_message(normalized_message)
                or len(normalized_message.split()) >= 2 and not normalized_message.endswith("?")):
            return None

        key = generate_cache_key(user_message)
        async with redis.Redis.from_url(REDIS_URL) as r:
            cached_data = await r.get(key)
            if cached_data:
                data = json.loads(cached_data)
                logger.info(f"[SEMANTIC CACHE HIT] Resposta rápida retornada do Redis para: {user_message[:40]}")
                return data.get("response")
    except Exception as e:
        logger.warning(f"Erro ao consultar cache semântico: {e}")
    return None

async def set_cached_response(user_message: str, ai_response: str):
    """Armazena a pergunta e a resposta no Redis para reuso econômico."""
    try:
        import re

        normalized_message = user_message.strip().lower()
        scheduling_terms = (
            "agendar", "consulta", "horário", "horario", "marcar", "cpf",
            "nascimento", "convênio", "convenio", "remarcar", "cancelar",
        )
        # Respostas personalizadas não podem ser reutilizadas entre pacientes.
        if (
            is_dynamic_conversation_message(normalized_message)
            or len(normalized_message.split()) >= 2 and not normalized_message.endswith("?")
        ):
            return

        from app.api.endpoints.settings import load_config
        cfg = load_config()
        if not cfg.get("semantic_cache_enabled", True):
            return

        # Não cachear agendamentos com dados privados, nomes específicos ou confirmações com datas dinâmicas, nem mensagens de segurança/bloqueio
        if any(term in ai_response.lower() for term in ["consulta marcada", "agendamento confirmado", "doutor(a)", "conselho de medicina", "prescrições de remédios"]):
            return

        # Cacheia APENAS respostas estáticas comprovadas (ex: localização, convênios aceitos, preparo geral de exames)
        if len(user_message.strip()) > 5 and len(ai_response.strip()) > 20:
            # Nunca cachear mensagens curtas de fluxo de agendamento (ex: "plano bradesco", "sim", "na parte da tarde")
            if any(term in user_message.lower() for term in ["plano", "convenio", "bradesco", "unimed", "sulamerica", "tarde", "manha", "hoje", "amanha"]):
                return
            key = generate_cache_key(user_message)
            payload = json.dumps({"query": user_message, "response": ai_response}, ensure_ascii=False)
            async with redis.Redis.from_url(REDIS_URL) as r:
                await r.setex(key, CACHE_TTL_SECONDS, payload)
                logger.info(f"[SEMANTIC CACHE SAVED] Cache salvo no Redis para: {user_message[:40]}")
    except Exception as e:
        logger.warning(f"Erro ao salvar no cache semântico: {e}")
