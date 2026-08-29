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
