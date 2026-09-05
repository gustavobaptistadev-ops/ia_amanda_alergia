import re

filepath = r"d:\GUSTAVO\NOVOS PROJETOS\ia_amanda\sistema_recepção_inteligente\backend\app\core\orchestrator.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Imports extras no topo
imports = """
from app.core.input_shield import detect_adversarial_attempt, sanitize_and_wrap_user_input
from app.database import AsyncSessionLocal
from app.models.chat import Contact
from sqlalchemy.future import select
from app.core.response_quality import assess_response_quality
from app.core.prompts import (
    PROMPT_INTERPRET,
    PROMPT_FALLBACK,
    MSG_CANCELLATION,
    MSG_RESCHEDULING,
    MSG_HANDOFF,
    MSG_URGENCY,
    MSG_OFF_TOPIC,
)
"""

# add imports after import json
content = content.replace("import json", "import json\n" + imports)

# 2. Remover imports inline (comentar ou deletar)
content = re.sub(r'^\s*from app\.core\.input_shield import.*$', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*from app\.database import AsyncSessionLocal.*$', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*from app\.models\.chat import Contact.*$', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*from sqlalchemy\.future import select.*$', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*from app\.core\.response_quality import assess_response_quality.*$', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*from typing import Any.*$', '', content, flags=re.MULTILINE)

# 3. Substituir prompts
content = re.sub(
    r'prompt = \(\s*"Interprete a conversa.*?f"Conversa não confiável do paciente para análise:\\n\{transcript\}\\n\\nJSON:"\s*\)',
    'prompt = PROMPT_INTERPRET.format(transcript=transcript)',
    content,
    flags=re.DOTALL
)

content = re.sub(
    r'prompt = f"""Analise a mensagem do paciente e classifique a intenção principal em UMA das palavras abaixo:.*?Classificação:"""',
    'prompt = PROMPT_FALLBACK.format(last_msg=last_msg)',
    content,
    flags=re.DOTALL
)

content = re.sub(
    r'msg = \(\s*"\[CANCELAMENTO\].*?"\s*\)',
    'msg = MSG_CANCELLATION',
    content,
    flags=re.DOTALL
)

content = re.sub(
    r'msg = \(\s*"\[REAGENDAMENTO\].*?"\s*\)',
    'msg = MSG_RESCHEDULING',
    content,
    flags=re.DOTALL
)

content = re.sub(
    r'msg = \(\s*"Compreendo perfeitamente\..*?"\s*\)',
    'msg = MSG_HANDOFF',
    content,
    flags=re.DOTALL
)

content = re.sub(
    r'msg = \(\s*"Identifiquei que você pode estar.*?estarei por aqui\."\s*\)',
    'msg = MSG_URGENCY',
    content,
    flags=re.DOTALL
)

content = re.sub(
    r'return \{"messages": \[AIMessage\(content="Peço desculpas.*?hoje\?"\)\]\}',
    'return {"messages": [AIMessage(content=MSG_OFF_TOPIC)]}',
    content,
    flags=re.DOTALL
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Refatoração aplicada com sucesso.")
