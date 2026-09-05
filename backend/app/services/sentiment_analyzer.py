import logging
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)
openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def detect_frustration(text: str) -> bool:
    """
    Analisa a mensagem do usuário em tempo real para detectar frustração extrema,
    raiva, ou desejo explícito de falar com um humano/atendente.
    Retorna True se detectar necessidade de escalonamento, False caso contrário.
    """
    if not text or len(text.strip()) < 3:
        return False

    system_prompt = (
        "Você é um classificador binário restrito e de ultrabaixa latência.\n"
        "Avalie a mensagem do paciente. Responda EXATAMENTE E APENAS com 'TRUE' se ele demonstrar:\n"
        "1. Extrema irritação, sarcasmo agressivo ou xingamentos.\n"
        "2. Exigência explícita para falar com humano, atendente, recepcionista, pessoa ou clínica.\n"
        "3. Frustração com a IA (ex: 'bot burro', 'você não entende', 'chama alguém').\n"
        "Caso contrário, responda EXATAMENTE E APENAS 'FALSE'. Nenhuma outra palavra é permitida."
    )

    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.0,
            max_tokens=5,
        )
        result = response.choices[0].message.content.strip().upper()
        
        if "TRUE" in result:
            logger.warning(f"⚠️ Frustração/Escalonamento detectado na mensagem: '{text}'")
            return True
            
        return False
    except Exception as e:
        logger.error(f"Erro no analisador de sentimento: {e}")
        return False  # Fail-safe (continua com a IA se falhar)
