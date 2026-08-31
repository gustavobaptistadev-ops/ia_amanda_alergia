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

import io
import pypdf
import re
from datetime import datetime

def check_expiration(data: dict):
    """Verifica se a carteirinha está vencida baseada na string expiration_date e injeta o alerta."""
    exp_date_str = data.get("expiration_date")
    if exp_date_str and str(exp_date_str).strip().lower() not in ["null", "none", ""]:
        nums = re.findall(r'\d+', str(exp_date_str))
        try:
            now = datetime.now()
            is_expired = False
            if len(nums) == 3:
                d, m, y = map(int, nums)
                if y < 100: y += 2000
                if datetime(y, m, d) < now: is_expired = True
            elif len(nums) == 2:
                m, y = map(int, nums)
                if y < 100: y += 2000
                if m == 12: next_m, next_y = 1, y+1
                else: next_m, next_y = m+1, y
                if datetime(next_y, next_m, 1) <= now: is_expired = True
            
            if is_expired:
                data["is_expired"] = True
                data["summary_for_chat"] = f"{data.get('summary_for_chat', '')} [ALERTA SISTEMA: A validade impressa ({exp_date_str}) indica que a carteirinha está vencida. Comunique o paciente com empatia.]"
        except Exception as d_err:
            logger.warning(f"[VISION OCR] Falha ao fazer parse da validade {exp_date_str}: {d_err}")

PDF_TEXT_PROMPT = """Você é um especialista sênior em faturamento médico e credenciamento hospitalar da Clínica Respirar.
Sua missão é analisar o texto extraído de um documento PDF enviado por um paciente no WhatsApp e identificar se é uma Carteirinha de Plano de Saúde / Convênio Médico ou documento de saúde.

Texto extraído do documento PDF:
\"\"\"{extracted_text}\"\"\"

Se FOR uma Carteirinha de Convênio ou Comprovante de Beneficiário (ex: Assefaz, Fundação Assefaz, Unimed, Bradesco, Amil, SulAmérica, Cassi, etc.), extraia minuciosamente:
1. is_health_card: true
2. operator: Nome da operadora (ex: Fundação Assefaz, Unimed, Bradesco Saúde, Amil, SulAmérica, etc.)
3. patient_name: Nome do beneficiário (ex: MATEUS SANT ANA DOS SANTOS, PEDRO SANT ANA DOS SANTOS, SILAS NEVES PEREIRA)
4. card_number: Número da matrícula / carteira (ex: 0001 0300 012963 007, 0001 0113 001426 861)
5. plan_name: Categoria / Plano (ex: ASSEFAZ SAFIRA, ASSEFAZ RUBI, AMB + HOSP + OBST)
6. coverage_area: Abrangência geográfica (ex: NACIONAL)
7. accommodation: Acomodação (ex: APARTAMENTO, ENFERMARIA)
8. expiration_date: Data de validade (ex: 31/07/2027)
9. ans_code: Registro na ANS (ex: 34.692-6)
10. summary_for_chat: Um resumo elegante para a Amanda confirmar com o paciente.

Se NÃO for carteirinha:
Retorne is_health_card: false e preencha summary_for_chat.

Responda estritamente em formato JSON válido com as chaves acima.
"""

async def process_health_card_document(file_bytes: bytes, filename: str = "") -> Dict[str, Any]:
    """
    Processa documentos PDF ou imagens de carteirinhas de convênio (Assefaz, Unimed, Bradesco, etc.).
    """
    # 1. Se for PDF, tenta extrair o texto embutido com pypdf primeiro
    if file_bytes.startswith(b"%PDF") or filename.lower().endswith(".pdf"):
        logger.info("[DOC OCR] Detectado arquivo PDF. Extraindo texto do PDF...")
        try:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            pdf_text = ""
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    pdf_text += t + "\n"
            
            if len(pdf_text.strip()) > 30:
                logger.info(f"[DOC OCR] Texto extraído com sucesso do PDF ({len(pdf_text)} caracteres). Analisando com LLM...")
                llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
                messages = [
                    SystemMessage(content="Você extrai dados de saúde e responde apenas em JSON."),
                    HumanMessage(content=PDF_TEXT_PROMPT.format(extracted_text=pdf_text))
                ]
                resp = await llm.ainvoke(messages)
                content = resp.content.strip()
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                data = json.loads(content)
                if data.get("is_health_card"):
                    check_expiration(data)
                    logger.info(f"[PDF SUCCESS] Carteirinha lida: Operadora={data.get('operator')}, Titular={data.get('patient_name')}, Matrícula={data.get('card_number')}")
                    return data
        except Exception as pdf_err:
            logger.warning(f"[DOC OCR] Falha ao extrair texto do PDF via pypdf: {pdf_err}")

    # 2. Se for imagem ou se o PDF precisar de visão computacional
    return await process_health_card_image(file_bytes)

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
                    {"type": "text", "text": "Analise esta imagem/carteirinha enviada pelo paciente e extraia os dados médicos com precisão."},
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
        
        # Validação CTO: Checa vencimento da carteirinha
        check_expiration(data)
                
        logger.info(f"[VISION OCR SUCCESS] Carteirinha processada: Operadora={data.get('operator')}, Matrícula={data.get('card_number')}, Titular={data.get('patient_name')}")
        return data
        
    except Exception as e:
        logger.error(f"[VISION OCR ERROR] Falha ao analisar carteirinha com Vision: {e}")
        return {
            "is_health_card": False,
            "error": str(e),
            "summary_for_chat": "Recebi seu documento/carteirinha, mas não consegui ler os dados com nitidez. Poderia me confirmar o nome do seu plano e o número da carteirinha por texto?"
        }
