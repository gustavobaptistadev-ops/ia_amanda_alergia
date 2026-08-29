import re
import logging

logger = logging.getLogger(__name__)

# Padrões conhecidos de Prompt Injection, Jailbreak, Escape e Off-Topic Exploitation
JAILBREAK_PATTERNS = [
    r"(?i)\bignore\s+(all\s+)?(previous|prior|above)\s+instructions\b",
    r"(?i)\besque[cç]a\s+(todas\s+as\s+)?(regras|instru[cç][oõ]es|diretrizes)\b",
    r"(?i)\b(dan|jailbreak|developer\s+mode|unfiltered\s+mode)\b",
    r"(?i)\b(system\s+override|bypass\s+safety|modo\s+sem\s+regras)\b",
    r"(?i)\b(repita|mostre|quais\s+s[aã]o)\s+(seu\s+)?(system\s+prompt|prompt\s+inicial|instru[cç][oõ]es\s+secretas)\b",
    r"(?i)\b(finja|aja|simule)\s+ser\s+(um\s+)?(m[eé]dico|doutor|hacker|ia\s+livre|programador|chef)\b",
    r"(?i)\b(voce\s+agora\s+e|agora\s+voce\s+responde\s+como)\b",
    r"(?i)\[system\]|\<system\>|\#\#\#\s*system|\[inst\]|\<start_of_turn\>",
    # Off-topic explícito (código, receitas, redação, cálculos)
    r"(?i)\b(escreva|gere|crie)\s+(um\s+)?(c[oó]digo|script|fun[cç][aã]o|programa|algoritmo)\s+(em\s+)?(python|javascript|java|c\+\+|sql|php|html)\b",
    r"(?i)\b(me\s+d[eê]|como\s+fazer|receita\s+de)\s+(um\s+)?(bolo|torta|p[aã]o|comida|culin[aá]ria)\b",
    r"(?i)\b(resolva|calcule)\s+(a\s+equa[cç][aã]o|o\s+fatorial|a\s+derivada|a\s+integral)\b"
]

def detect_adversarial_attempt(text: str) -> bool:
    """Verifica se o texto contém padrões de ataque adversarial ou tentativa de jailbreak."""
    if not text:
        return False
    for pattern in JAILBREAK_PATTERNS:
        if re.search(pattern, text):
            logger.warning(f"Ataque adversarial / Prompt Injection detectado no input: {text[:80]}...")
            return True
    return False

def sanitize_and_wrap_user_input(text: str) -> str:
    """
    Envelopa o input do paciente dentro de tags delimitadoras seguras XML (<user_message>),
    removendo tentativas de injeção de delimitadores de sistema.
    """
    if not text:
        return ""

    # Neutraliza falsas tags de sistema que o usuário possa ter digitado
    sanitized = text.replace("<system>", "&lt;system&gt;").replace("</system>", "&lt;/system&gt;")
    sanitized = sanitized.replace("[INST]", "").replace("[/INST]", "")
    sanitized = sanitized.replace("### System:", "").replace("--- BEGIN SYSTEM ---", "")

    return f"<user_message>\n{sanitized.strip()}\n</user_message>"
