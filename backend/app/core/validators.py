import re

def validate_cpf(cpf_raw: str) -> bool:
    """
    Valida um CPF utilizando o algoritmo oficial de dígitos verificadores da Receita Federal.
    Aceita formatos: '123.456.789-00', '12345678900' ou com espaços.
    """
    if not cpf_raw:
        return False

    # Remove tudo que não for dígito
    digits = re.sub(r"\D", "", str(cpf_raw))

    # CPF deve ter exatamente 11 dígitos
    if len(digits) != 11:
        return False

    # Elimina CPFs com todos os dígitos iguais (ex: '11111111111')
    if digits == digits[0] * 11:
        return False

    # Cálculo do primeiro dígito verificador
    soma = sum(int(digits[i]) * (10 - i) for i in range(9))
    resto = (soma * 10) % 11
    digito1 = 0 if resto == 10 else resto

    if int(digits[9]) != digito1:
        return False

    # Cálculo do segundo dígito verificador
    soma = sum(int(digits[i]) * (11 - i) for i in range(10))
    resto = (soma * 10) % 11
    digito2 = 0 if resto == 10 else resto

    return int(digits[10]) == digito2

def sanitize_text(text: str, max_length: int = 120) -> str:
    """Sanitiza strings de entrada para evitar Calendar Injection e truncamentos."""
    if not text:
        return ""
    # Remove caracteres de controle e quebras de linha perigosas
    clean = re.sub(r"[\r\n\t]", " ", str(text)).strip()
    return clean[:max_length]

import html

def sanitize_html(text: str) -> str:
    """Escapa tags HTML contra ataques de XSS em mensagens do painel."""
    if not text:
        return ""
    return html.escape(str(text))

def mask_phone_for_logs(phone: str) -> str:
    """Mascara o número de telefone para logs em conformidade com a LGPD (ex: 5561****2495)."""
    if not phone or len(phone) < 8:
        return "***"
    clean = re.sub(r"\D", "", str(phone))
    if len(clean) >= 8:
        return f"{clean[:4]}****{clean[-4:]}"
    return f"{clean[:2]}****"

def mask_cpf_for_logs(cpf: str) -> str:
    """Mascara o CPF para logs em conformidade com a LGPD (ex: ***.***.123-**)."""
    if not cpf:
        return "***"
    digits = re.sub(r"\D", "", str(cpf))
    if len(digits) == 11:
        return f"***.***.{digits[6:9]}-**"
    return "***"
