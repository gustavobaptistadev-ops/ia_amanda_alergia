import logging
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

llm_validador = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)

VALIDADOR_PROMPT = """Você é o Diretor Clínico e Auditor de Qualidade da Clínica Respirar.
Sua única tarefa é revisar a resposta que a IA (Amanda) gerou para um paciente, baseando-se nas regras da LGPD e no Conselho de Medicina.

Verifique APENAS estas condições:
1. A Amanda tentou prescrever algum medicamento?
2. A Amanda tentou dar algum diagnóstico médico assertivo?
3. A Amanda vazou informações de cartão de crédito, senhas ou dados sensíveis?
4. A Amanda foi desrespeitosa ou usou palavras vulgares?

Se a resposta violar QUALQUER UMA dessas regras, responda APENAS com a palavra: "REPROVADO".
Se a resposta estiver segura e dentro dos limites da recepcionista, responda APENAS com a palavra: "APROVADO".

Resposta gerada pela IA a ser avaliada:
"{ai_response}"
"""

def validar_resposta(ai_response: str) -> bool:
    """Retorna True se a resposta for APROVADA, False se for REPROVADA."""
    logger.info("Validando resposta da IA por segurança (Guardrails)...")
    try:
        messages = [
            SystemMessage(content="Você avalia as mensagens baseando-se estritamente nas regras. Responda apenas APROVADO ou REPROVADO."),
            HumanMessage(content=VALIDADOR_PROMPT.format(ai_response=ai_response))
        ]
        
        resultado = llm_validador.invoke(messages).content.strip().upper()
        
        if "REPROVADO" in resultado:
            logger.warning(f"Resposta barrada pelo Guardrail: {ai_response}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Erro no validador de guardrails: {e}")
        # Em caso de falha do validador, falhamos aberto (aprovado) ou fechado (reprovado)?
        # Geralmente falhamos seguro (reprovado) em saúde.
        return False
