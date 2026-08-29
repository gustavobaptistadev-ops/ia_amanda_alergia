import base64
import json
import logging
from typing import Optional, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

VISION_PROMPT = """Você é um especialista sênior em faturamento médico e credenciamento hospitalar da Clínica Respirar.
Sua missão é analisar uma foto/imagem enviada por um paciente no WhatsApp e identificar se é uma Carteirinha de Plano de Saúde / Convênio Médico ou documento pessoal.

Se FOR uma Carteirinha de Convênio, extraia minuciosamente os seguintes dados estruturados:
1. is_health_card: true
2. operator: Nome da operadora (ex: Unimed, Bradesco Saúde, Amil, SulAmérica, NotreDame Intermédica, Cassi, Petrobras, Geap, Allianz, Porto Seguro, Care Plus, Omint, etc.)
3. patient_name: Nome do beneficiário impresso na carteirinha
4. card_number: Número da matrícula / carteira (com dígitos verificadores se houver)
5. plan_name: Nome da categoria / linha do plano (ex: Nacional Flex, Top Nacional, S380, Especial 100, Smart 200, Unimed Nacional Superior, etc.)
6. coverage_area: Abrangência geográfica (ex: Nacional, Estadual, Grupo de Municípios)
7. accommodation: Padrão de acomodação (ex: Apartamento / Quarto Individual, Enfermaria / Quarto Coletivo, Ambulatorial)
8. expiration_date: Data de validade (se visível)
9. ans_code: Registro do produto na ANS (se visível)
10. summary_for_chat: Um resumo curto e elegante em 1 parágrafo dos dados encontrados para a Amanda confirmar com o paciente.

Se a imagem NÃO for uma carteirinha de plano de saúde (ex: foto aleatória, meme, documento não médico):
Retorne is_health_card: false e preencha summary_for_chat informando o que parece ser a imagem.

IMPORTANTE: Responda estritamente em formato JSON válido conforme as chaves acima.
"""

async def process_health_card_image(image_bytes: bytes) -> Dict[str, Any]:
    """
    Processa os bytes de uma imagem usando GPT-4o Vision e retorna os dados estruturados da carteirinha.
    """
    try:
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        
        llm_vision = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.0,
            max_tokens=1000
        )
        
        messages = [
            SystemMessage(content=VISION_PROMPT),
            HumanMessage(
                content=[
                    {"type": "text", "text": "Analise esta imagem enviada pelo paciente e extraia os dados da carteirinha médica se aplicável."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64_image}",
                            "detail": "high"
                        }
                    }
                ]
            )
        ]
        
        logger.info("[VISION OCR] Enviando imagem de carteirinha para análise com GPT-4o Vision...")
        response = await llm_vision.ainvoke(messages)
        content = response.content.strip()
        
        # Limpeza de markdown se a LLM responder com ```json ... ```
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        data = json.loads(content)
        logger.info(f"[VISION OCR SUCCESS] Carteirinha processada: Operadora={data.get('operator')}, Matrícula={data.get('card_number')}")
        return data
        
    except Exception as e:
        logger.error(f"[VISION OCR ERROR] Falha ao analisar carteirinha com Vision: {e}")
        return {
            "is_health_card": False,
            "error": str(e),
            "summary_for_chat": "Recebi sua imagem, mas não consegui ler os dados da carteirinha com nitidez. Poderia me enviar outra foto mais nítida ou confirmar o número do seu plano por texto?"
        }
