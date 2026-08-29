import re
import base64
import unicodedata
import logging

logger = logging.getLogger(__name__)

# Padrões de Jailbreak, Prompt Injection e Off-Topic
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
    r"(?i)\b(resolva|calcule)\s+(a\s+equa[cç][aã]o|o\s+fatorial|a\s+derivada|a\s+integral)\b",
    # Comandos de ofuscação (Base64 / Hex / Cifras)
    r"(?i)\b(decodifique|decript|decode|desembaralhe|execute\s+o\s+base64)\b"
]

def normalize_text(text: str) -> str:
    """Remove caracteres invisíveis (zero-width) e normaliza acentuações e leetspeak básico."""
    if not text:
        return ""
    # Remove caracteres de largura zero e invisíveis
    text = re.sub(r"[\u200B-\u200D\uFEFF]", "", text)
    # Normalização unicode (NFKD)
    normalized = unicodedata.normalize("NFKD", text)
    # Substituições simples de leetspeak comuns
    leet_map = {"0": "o", "1": "i", "3": "e", "4": "a", "@": "a", "5": "s", "7": "t", "$": "s"}
    for k, v in leet_map.items():
        normalized = normalized.replace(k, v)
    return normalized

def detect_base64_injection(text: str) -> bool:
    """Verifica se há blocos de Base64 suspeitos de injeção dentro do texto."""
    if not text:
        return False
    # Procura tokens longos em base64 (20+ caracteres alfanuméricos terminados ou não em =)
    b64_matches = re.findall(r"[A-Za-z0-9+/]{20,}={0,2}", text)
    for token in b64_matches:
        try:
            decoded = base64.b64decode(token).decode("utf-8", errors="ignore")
            # Se a string decodificada contiver palavras de ataque, bloqueia
            if any(re.search(p, decoded) for p in JAILBREAK_PATTERNS):
                logger.warning(f"Payload Base64 oculto detectado: {decoded[:50]}...")
                return True
        except Exception:
            pass
    return False

def detect_adversarial_attempt(text: str) -> bool:
    """Verifica se o texto contém padrões de ataque adversarial, ofuscação ou tentativa de jailbreak."""
    if not text:
        return False

    # 1. Checa injeção Base64 oculta
    if detect_base64_injection(text):
        return True

    # 2. Normaliza texto e analisa regex
    clean_text = normalize_text(text)
    for pattern in JAILBREAK_PATTERNS:
        if re.search(pattern, clean_text):
            logger.warning(f"Ataque adversarial / Prompt Injection detectado no input: {text[:80]}...")
            return True
            
    return False

def sanitize_and_wrap_user_input(text: str, max_chars: int = 1500) -> str:
    """
    Envelopa o input do paciente dentro de tags delimitadoras seguras XML (<user_message>),
    limitando o comprimento máximo a 1500 caracteres (Anti-Token Flooding)
    e neutralizando tentativas de injeção de delimitadores de sistema.
    """
    if not text:
        return ""

    # Trava de tamanho máximo contra DDoS Semântico
    truncated = text[:max_chars].strip()

    # Neutraliza falsas tags de sistema que o usuário possa ter digitado
    sanitized = truncated.replace("<system>", "&lt;system&gt;").replace("</system>", "&lt;/system&gt;")
    sanitized = sanitized.replace("[INST]", "").replace("[/INST]", "")
    sanitized = sanitized.replace("### System:", "").replace("--- BEGIN SYSTEM ---", "")

    return f"<user_message>\n{sanitized}\n</user_message>"
